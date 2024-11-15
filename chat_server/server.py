#!/usr/bin/python3

import errno
import json
import select
import socket
import sys
import threading
import queue

from absl import app, flags

import message_pb2 as pb


FLAGS = flags.FLAGS

# 서버 설정 옵션
flags.DEFINE_string(name='ip', default='127.0.0.1', help='서버의 IP 주소')
flags.DEFINE_integer(name='port', default=10207, help='서버의 port 번호')
flags.DEFINE_enum(name='format', default='json', enum_values=['json', 'protobuf'], help='메시지 포맷')
flags.DEFINE_integer(name='thread', default=2, help='서버의 thread 개수') # thread의 기본값은 2로 설정



class SocketClosed(RuntimeError):
  pass


class NoTypeFieldInMessage(RuntimeError):
  pass


class UnknownTypeInMessage(RuntimeError):
  def __self__(self, _type):
    self.type = _type

  def __str__(self):
    return str(self.type)


# 작업 큐
message_queue = queue.Queue()  # 작업 큐
queue_lock = threading.Lock()  # 작업 큐에 대한 락
queue_condition = threading.Condition(queue_lock)  # 작업 큐의 조건 변수


# 소켓 관리
active_socket = []  # 서버 및 연결된 클라이언트 소켓 관리용 리스트
active_socket_lock = threading.Lock()  # 연결된 소켓 리스트에 대한 락


# 채팅 목록
chat_rooms = {}  # 채팅방 목록 저장용 딕셔너리
chat_rooms_lock = threading.Lock()  # 채팅방 목록에 대한 락


# 클라이언트의 데이터
client_data = {}  # 클라이언트별 이름, 채팅 관련 데이터 저장용 딕셔너리
client_data_lock = threading.Lock()  # 클라이언트 데이터에 대한 락


# 메시지 처리용 변수(각 소켓에 대해 개별 관리)
socket_buffer = {} # 클라이언트 소켓별 버퍼
current_message_len = {} # 클라이언트 소켓별 메시지 길이
current_protobuf_type = {} # 클라이언트 소켓별 Protobuf 타입
client_socket_lock = {} # 클라이언트 소켓별 락


# 서버 종료 이벤트 플래그
shutdown_event = threading.Event()


# 서버 소켓 생성
def setup_server(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((ip, port))
    server_socket.listen()
    server_socket.setblocking(False)
    print(f'서버가 {ip}:{port} 로 설정됨')

    return server_socket


# 클라이언트로 메시지를 전송
def send_messages_to_client(client_socket, data):

    for msg in data:
        if FLAGS.format == 'json':
            serialized = bytes(json.dumps(msg), encoding='utf-8')
        else:
            serialized = msg.SerializeToString()

        # TCP 에서 send() 함수는 일부만 전송될 수도 있다.
        # 따라서 보내려는 데이터를 다 못 보낸 경우 재시도 해야된다.
        to_send = len(serialized)
        to_send_big_endian = int.to_bytes(to_send, byteorder='big', length=2)

        # 받는 쪽에서 어디까지 읽어야 되는지 message boundary 를 알 수 있게끔 2byte 길이를 추가한다.
        serialized = to_send_big_endian + serialized

        offset = 0
        while offset < len(serialized):
            try:
                num_sent = client_socket.send(serialized[offset:])
                if num_sent <= 0:
                    raise RuntimeError('Send failed')
                offset += num_sent
            except BlockingIOError:
                continue
            except Exception as err:
                print(f'send_messages_to_client()에서 에러 발생: {err}')
                break


# 같은 방 다른 클라이언트에게 메시지 전송
def on_sc_notify_room_members(client_socket, text):
    messages = []

    # 클라이언트가 속한 방의 ID를 가져옴
    with client_data_lock:
        room_id = client_data[client_socket].get('room')
    if not room_id:
        # 방에 속하지 않은 경우 작업 중단
        return

    # 메시지 형식에 따라 알림 메시지 작성
    if FLAGS.format == 'json':
        message = {
            'type': 'SCSystemMessage',
            'text': text,
        }
        messages.append(message)
    else:
        message = pb.Type()
        message.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE
        messages.append(message)

        message = pb.SCSystemMessage()
        message.text = text
        messages.append(message)

    # 같은 방에 있는 다른 클라이언트에게 알림 전송
    with chat_rooms_lock:
        room_members = chat_rooms.get(room_id, {}).get('members', [])
    for member_socket in room_members:
        if member_socket != client_socket:
            try:
                send_messages_to_client(member_socket, messages)
            except Exception as err:
                print(f'on_sc_notify_room_members()에서 에러 발생: {err}')


# 클라이언트의 이름 변경 요청 처리
def on_cs_name(client_socket, data):
    old_name = None
    new_name = None
    messages = []
    if FLAGS.format == 'json':
        new_name = data.get('name', None)
        if new_name:
            with client_data_lock:
                old_name = client_data[client_socket].get('name')
                client_data[client_socket]['name'] = new_name
            
            message = {
                'type': 'SCSystemMessage',
                'text': f'이름이 {new_name} 으/로 변경되었습니다.',
            }
            messages.append(message)
    else:
        new_name = data.name
        if new_name:
            with client_data_lock:
                old_name = client_data[client_socket].get('name')
                client_data[client_socket]['name'] = new_name
            
            message = pb.Type()
            message.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE
            messages.append(message)

            message = pb.SCSystemMessage()
            message.text = f'이름이 {new_name} 으/로 변경되었습니다.'
            messages.append(message)

    send_messages_to_client(client_socket, messages)

    # 이름이 변경된 경우 다른 사용자에게 알림
    if old_name and old_name != new_name:
        name_notification = f'{old_name} 님의 이름이 {new_name} 으/로 변경되었습니다.'
        on_sc_notify_room_members(client_socket, name_notification)


# 클라이언트의 방 목록 요청 처리
def on_cs_rooms(client_socket, data):
    rooms_data = []
    messages = []

    # 현재 존재하는 방의 정보를 가져옴
    with chat_rooms_lock:
        for room_id, room_info in chat_rooms.items():
            room_data = {
                'roomId': room_id,
                'title': room_info['title'],
                'members': [],
            }
            # 각 방의 멤버 이름 추가
            for member_socket in room_info['members']:
                with client_data_lock:
                    member_name = client_data[member_socket].get('name')
                    room_data['members'].append(member_name)
            
            rooms_data.append(room_data)

    # 방 목록 결과 메시지 작성
    if FLAGS.format == 'json':
        message = {
            'type': 'SCRoomsResult',
            'rooms': rooms_data,
        }
        messages.append(message)
    else:
        message = pb.Type()
        message.type = pb.Type.MessageType.SC_ROOMS_RESULT
        messages.append(message)

        message = pb.SCRoomsResult()
        for room in rooms_data:
            room_info = message.rooms.add()
            room_info.roomId = room['roomId']
            room_info.title = room['title']
            room_info.members.extend(room['members'])
        messages.append(message)

    send_messages_to_client(client_socket, messages)


# 클라이언트의 방 생성 요청 처리
def on_cs_create_room(client_socket, data):
    title = None
    messages = []

    # 클라이언트가 이미 방에 참여 중인지 확인
    with client_data_lock:
        joined_room = client_data[client_socket].get('room')
    if joined_room:
        # 이미 방에 참여 중이면 방 생성 불가 메시지 전송
        text = '대화 방에 있을 때는 방을 개설 할 수 없습니다.'
        if FLAGS.format == 'json':
            message = {
                'type': 'SCSystemMessage',
                'text': text,
            }
            messages.append(message)
        else:
            message = pb.Type()
            message.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE
            messages.append(message)

            message = pb.SCSystemMessage()
            message.text = text
            messages.append(message)
        
        send_messages_to_client(client_socket, messages)
        return
    else:
        # 클라이언트가 방에 참여 중이지 않으면 새로운 방 생성
        if FLAGS.format == 'json':
            title = data.get('title')
        else:
            title = data.title

        # 새로운 방 ID 생성 및 방 정보 등록
        with chat_rooms_lock:
            new_room_id = max(chat_rooms.keys(), default=0) + 1
            chat_rooms[new_room_id] = {
                'title': title,
                'members': [],
            }
        
        # 방 생성 완료 메시지 작성
        text = f'방제[{title}] 이/가 생성되었습니다.'
        if FLAGS.format == 'json':
            message = {
                'type': 'SCSystemMessage',
                'text': text,
            }
            messages.append(message)
            send_messages_to_client(client_socket, messages)
            # 생성된 방으로 자동 입장
            on_cs_join_room(client_socket, {'roomId': new_room_id})
        else:
            message = pb.Type()
            message.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE
            messages.append(message)

            message = pb.SCSystemMessage()
            message.text = text
            messages.append(message)
            send_messages_to_client(client_socket, messages)
            message = pb.CSJoinRoom()
            message.roomId = new_room_id
            # 생성된 방으로 자동 입장
            on_cs_join_room(client_socket, message)
        

# 클라이언트의 방 입장 요청 처리
def on_cs_join_room(client_socket, data):
    room_id = None
    messages = []

    # 클라이언트가 이미 다른 방에 참여 중인지 확인
    with client_data_lock:
        joined_room = client_data[client_socket].get('room')
    if joined_room:
        # 이미 참여 중인 방이 있으면 방 입장 불가 메시지 전송
        text = '대화 방에 있을 때는 다른 방에 들어갈 수 없습니다.'
        if FLAGS.format == 'json':
            message = {
                'type': 'SCSystemMessage',
                'text': text,
            }
            messages.append(message)
        else:
            message = pb.Type()
            message.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE
            messages.append(message)

            message = pb.SCSystemMessage()
            message.text = text
            messages.append(message)
        
        send_messages_to_client(client_socket, messages)
        return
    
    if FLAGS.format == 'json':
        room_id = data.get('roomId')
    else:
        room_id = data.roomId
    
    # 방 ID 유효성 확인
    with chat_rooms_lock:
        if room_id not in chat_rooms:
            # 방이 존재하지 않으면 에러 메시지 전송
            text = '대화방이 존재하지 않습니다.'
            if FLAGS.format == 'json':
                message = {
                    'type': 'SCSystemMessage',
                    'text': text,
                }
                messages.append(message)
            else:
                message = pb.Type()
                message.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE
                messages.append(message)

                message = pb.SCSystemMessage()
                message.text = text
                messages.append(message)

            send_messages_to_client(client_socket, messages)
            return
        
        # 방에 클라이언트 추가
        chat_rooms[room_id]['members'].append(client_socket)
        title = chat_rooms[room_id]['title']
    
    # 클라이언트 데이터에 방 ID 업데이트
    with client_data_lock:
        client_data[client_socket]['room'] = room_id
        user_name = client_data[client_socket].get('name')

    # 같은 방에 있는 멤버들에게 입장 알림 전송
    join_notification = f'[{user_name}] 님이 입장했습니다.'
    on_sc_notify_room_members(client_socket, join_notification)

    # 방 입장 성공 메시지 작성 및 전송
    text = f"방제[{title}] 방에 입장했습니다."
    if FLAGS.format == 'json':
        message = {
            'type': 'SCSystemMessage',
            'text': text,
        }
        messages.append(message)
    else:
        message = pb.Type()
        message.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE
        messages.append(message)

        message = pb.SCSystemMessage()
        message.text = text
        messages.append(message)
    
    send_messages_to_client(client_socket, messages)


# 클라이언트의 방 퇴장 요청 처리
def on_cs_leave_room(client_socket, data):
    messages = []

    try:
        # 클라이언트의 현재 방 정보를 가져옴
        with client_data_lock:
            room_id = client_data[client_socket].get('room')
            user_name = client_data[client_socket].get('name')

        if not room_id:
            # 클라이언트가 방에 들어가 있지 않은 경우 에러 메시지 전송
            text = '현재 대화방에 들어가 있지 않습니다.'
            if FLAGS.format == 'json':
                message = {
                    'type': 'SCSystemMessage',
                    'text': text,
                }
                messages.append(message)
            else:
                message_type = pb.Type()
                message_type.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE
                messages.append(message_type)

                system_message = pb.SCSystemMessage()
                system_message.text = text
                messages.append(system_message)

            send_messages_to_client(client_socket, messages)
            return

        # 방에서 나가기 전 다른 멤버들에게 알림 전송
        leave_notification = f'[{user_name}] 님이 퇴장했습니다.'
        on_sc_notify_room_members(client_socket, leave_notification)

        room_title = ''
        # 방 목록에서 클라이언트 제거
        with chat_rooms_lock:
            if room_id in chat_rooms:
                room_title = chat_rooms.get(room_id, {}).get('title')
                chat_rooms[room_id]['members'].remove(client_socket)
                # 방에 남은 사람이 없다면 방 삭제
                if not chat_rooms[room_id]['members']:
                    print(f"방제[{room_title}] 대화 방에 남은 사람이 없습니다. 대화 방을 삭제합니다.")
                    del chat_rooms[room_id]

        # 클라이언트의 방 정보 초기화
        with client_data_lock:
            client_data[client_socket]['room'] = None

        # 퇴장 완료 메시지 작성
        text = f'방제[{room_title}] 대화 방에서 퇴장했습니다.'
        if FLAGS.format == 'json':
            message = {'type': 'SCSystemMessage', 'text': text}
            messages.append(message)
        else:
            message_type = pb.Type()
            message_type.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE
            messages.append(message_type)
            system_message = pb.SCSystemMessage()
            system_message.text = text
            messages.append(system_message)

        send_messages_to_client(client_socket, messages)
    except Exception as err:
        print(f'on_cs_leave_room()에서 에러 발생: {err}')


# 클라이언트의 채팅 메시지 처리
def on_cs_chat(client_socket, data):
    room_id = None
    messages = []

    # 클라이언트가 속한 방의 ID를 가져옴
    with client_data_lock:
        room_id = client_data[client_socket].get('room')
    if not room_id:
        # 클라이언트가 방에 들어가 있지 않은 경우 에러 메시지 전송
        text = '현재 대화방에 들어가 있지 않습니다.'
        if FLAGS.format == 'json':
            message = {
                'type': 'SCSystemMessage',
                'text': text,
            }
            messages.append(message)
        else:
            message = pb.Type()
            message.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE
            messages.append(message)

            message = pb.SCSystemMessage()
            message.text = text
            messages.append(message)
        
        send_messages_to_client(client_socket, messages)
        return

    # 채팅 메시지와 전송할 사용자 정보 가져오기
    text = None
    with client_data_lock:
        user_name = client_data[client_socket].get('name')
    if FLAGS.format == 'json':
        text = data.get('text')
        
        message = {
            'type': 'SCChat',
            'member': user_name,
            'text': text,
        }
        messages.append(message)
    else:
        text = data.text

        message = pb.Type()
        message.type = pb.Type.MessageType.SC_CHAT
        messages.append(message)

        message = pb.SCChat()
        message.member = user_name
        message.text = text
        messages.append(message)
    
    # 다른 사용자들에게 메시지 전송
    with chat_rooms_lock:
        for member_socket in chat_rooms[room_id]['members']:
            if member_socket != client_socket:
                send_messages_to_client(member_socket, messages)


# 서버 종료 명령 처리
def on_cs_shutdown(client_socket, data):
    # 서버 종료 이벤트 플래그 설정
    shutdown_event.set()
    print('shutdown_event가 설정되었습니다.')

    # 대기 중인 워커 쓰레드 모두 깨우기
    with queue_condition:
            queue_condition.notify_all()


json_message_handlers = {
    'CSName': on_cs_name,
    'CSRooms': on_cs_rooms,
    'CSCreateRoom': on_cs_create_room,
    'CSJoinRoom': on_cs_join_room,
    'CSLeaveRoom': on_cs_leave_room,
    'CSChat': on_cs_chat,
    'CSShutdown': on_cs_shutdown,
}

protobuf_message_handlers = {
    pb.Type.MessageType.CS_NAME: on_cs_name,
    pb.Type.MessageType.CS_ROOMS: on_cs_rooms,
    pb.Type.MessageType.CS_CREATE_ROOM: on_cs_create_room,
    pb.Type.MessageType.CS_JOIN_ROOM: on_cs_join_room,
    pb.Type.MessageType.CS_LEAVE_ROOM: on_cs_leave_room,
    pb.Type.MessageType.CS_CHAT: on_cs_chat,
    pb.Type.MessageType.CS_SHUTDOWN: on_cs_shutdown,
}

protobuf_message_parsers = {
    pb.Type.MessageType.CS_NAME: pb.CSName.FromString,
    pb.Type.MessageType.CS_ROOMS: pb.CSRooms.FromString,
    pb.Type.MessageType.CS_CREATE_ROOM: pb.CSCreateRoom.FromString,
    pb.Type.MessageType.CS_JOIN_ROOM: pb.CSJoinRoom.FromString,
    pb.Type.MessageType.CS_LEAVE_ROOM: pb.CSLeaveRoom.FromString,
    pb.Type.MessageType.CS_CHAT: pb.CSChat.FromString,
    pb.Type.MessageType.CS_SHUTDOWN: pb.CSShutdown.FromString,
}


# 클라이언트 소켓에서 수신한 데이터를 처리
def process_socket(client_socket):
    # 소켓이 이미 닫혀 있는지 확인
    if client_socket.fileno() == -1:
        raise SocketClosed()

    with client_socket_lock[client_socket]:
        if client_socket not in socket_buffer:
            socket_buffer[client_socket] = b''
        if client_socket not in current_message_len:
            current_message_len[client_socket] = None
        if client_socket not in current_protobuf_type:
            current_protobuf_type[client_socket] = None

        try:
            # 클라이언트로부터 데이터 수신
            received_buffer = client_socket.recv(65535)
            if not received_buffer:
                raise SocketClosed()
            
            socket_buffer[client_socket] += received_buffer

            while True:
                if current_message_len[client_socket] is None:
                    if len(socket_buffer[client_socket]) < 2:
                        return
                    current_message_len[client_socket] = int.from_bytes(socket_buffer[client_socket][:2], byteorder='big')
                    socket_buffer[client_socket] = socket_buffer[client_socket][2:]

                if len(socket_buffer[client_socket]) < current_message_len[client_socket]:
                    return

                serialized = socket_buffer[client_socket][:current_message_len[client_socket]]
                socket_buffer[client_socket] = socket_buffer[client_socket][current_message_len[client_socket]:]
                current_message_len[client_socket] = None

                if FLAGS.format == 'json':
                    msg = json.loads(serialized)
                    msg_type = msg.get('type', None)
                    if not msg_type:
                        raise NoTypeFieldInMessage()
                    if msg_type in json_message_handlers:
                        json_message_handlers[msg_type](client_socket, msg)
                    else:
                        raise UnknownTypeInMessage(msg_type)
                else:
                    if current_protobuf_type[client_socket] is None:
                        msg = pb.Type.FromString(serialized)
                        if msg.type in protobuf_message_parsers and msg.type in protobuf_message_handlers:
                            current_protobuf_type[client_socket] = msg.type
                        else:
                            raise UnknownTypeInMessage(msg.type)
                    else:
                        msg = protobuf_message_parsers[current_protobuf_type[client_socket]](serialized)
                        try:
                            protobuf_message_handlers[current_protobuf_type[client_socket]](client_socket, msg)
                        finally:
                            current_protobuf_type[client_socket] = None
        except BlockingIOError:
            pass


def worker():
    print(f'{threading.current_thread().name} 시작')
    while not shutdown_event.is_set():
        with queue_condition:
            while message_queue.empty() and not shutdown_event.is_set():
                queue_condition.wait()
            
            if shutdown_event.is_set():
                break

            client_socket = message_queue.get()
            message_queue.task_done()

        if client_socket and client_socket.fileno() != -1:
            try:
                process_socket(client_socket)
            except SocketClosed:
                close_client_socket(client_socket)


# 서버가 실행 중인 상태에서 클라이언트의 접속 종료를 처리
def close_client_socket(client_socket):
    with client_socket_lock[client_socket]:
        if client_socket.fileno() == -1:
            return

        # 소켓 목록에서 제거
        with active_socket_lock:
            if client_socket in active_socket:
                active_socket.remove(client_socket)

        # 클라이언트 데이터 정리
        with client_data_lock:
            client_data.pop(client_socket, None)

        # 버퍼 및 상태 정보 정리
        socket_buffer.pop(client_socket, None)
        current_message_len.pop(client_socket, None)
        current_protobuf_type.pop(client_socket, None)
        client_socket_lock.pop(client_socket, None)
    
        try:
            client_socket.close()
        except Exception as e:
            print(f"close_client_socket() 클라이언트 소켓 종료 중 오류: {e}")


def main(argv):
    if not FLAGS.ip:
        print('서버가 사용할 IP 주소를 지정해야 됩니다.')
        sys.exit(1)

    if not FLAGS.port:
        print('서버가 사용할 Port 번호를 지정해야 됩니다.')
        sys.exit(2)

    if not FLAGS.format:
        print('서버가 사용할 format을 지정해야 됩니다.')
        sys.exit(3)

    if not FLAGS.thread:
        print('서버가 사용할 thread의 개수를 지정해야 됩니다.')
        sys.exit(4)
    
    # 서버 소켓 설정
    server_socket = setup_server(FLAGS.ip, FLAGS.port)
    with active_socket_lock:
        active_socket.append(server_socket)

    # 워커 스레드 생성
    threads = []
    for i in range(FLAGS.thread):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)
    print(f'총 생성된 스레드의 개수: {len(threads)}')

    try:
        while not shutdown_event.is_set():
            with active_socket_lock:
                readable, _, _ = select.select(active_socket, [], [], 0.2)

            # 종료 이벤트 설정 시 루프 종료
            if shutdown_event.is_set():
                break

            for socket in readable:
                if shutdown_event.is_set():
                    break

                if socket is server_socket:
                    # 새로운 클라이언트 연결 처리
                    client_socket, client_address = server_socket.accept()
                    client_socket.setblocking(False)
                    print(f'클라이언트 연결됨: {client_address}')
                    with active_socket_lock:
                        active_socket.append(client_socket)
                    with client_data_lock:
                        client_data[client_socket] = {'name': str(client_address)}
                    client_socket_lock[client_socket] = threading.Lock()
                else:
                    # 클라이언트 소켓을 작업 큐에 추가
                    if socket.fileno() == -1:
                        continue
                    with queue_condition:
                        if socket not in message_queue.queue and not shutdown_event.is_set():
                            message_queue.put(socket)
                            queue_condition.notify_all()
    finally:
        # 모든 소켓 정리
        with active_socket_lock:
            for socket in active_socket:
                if socket.fileno() != -1:
                    try:
                        socket.close()
                    except Exception as err:
                        print(f"main()에서 소켓 닫기 중 오류: {err}")

        # 모든 워커 스레드가 종료될 때까지 대기
        for thread in threads:
            thread.join()
            print(f'워커 스레드 {thread.name} 종료됨')

        print('모든 스레드가 종료되었습니다. 서버를 종료합니다.')


if __name__ == '__main__':
    app.run(main)