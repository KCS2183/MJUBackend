#!/usr/bin/python3

import sys
import socket

HOST = ''
PORT = 10207
BUFSIZE = [2048] # 임시로 지정
ADDR = (HOST, PORT)

# 소켓 생성
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 서버 구현 작업 중에는 바로 재사용 할 수 있도록 임시 설정
serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 소켓 바인딩
serverSocket.bind(ADDR)
print('bind')

serverSocket.listen(100)
print('listen')

clientSocket, addr_info = serverSocket.accept()
print('accept')
print('--client information--')
print(clientSocket)

# 클라이언트로부터 메시지를 가져옴
data = clientSocket.recv(65535)
print('recieve data : ', data.decode())

# 소켓 종료 
clientSocekt.close()
serverSocket.close()
print('close')