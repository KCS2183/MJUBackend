# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: message.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\rmessage.proto\x12\x03mju\"\xe6\x01\n\x04Type\x12#\n\x04type\x18\x01 \x02(\x0e\x32\x15.mju.Type.MessageType\"\xb8\x01\n\x0bMessageType\x12\x0b\n\x07\x43S_NAME\x10\x00\x12\x0c\n\x08\x43S_ROOMS\x10\x01\x12\x12\n\x0e\x43S_CREATE_ROOM\x10\x02\x12\x10\n\x0c\x43S_JOIN_ROOM\x10\x03\x12\x11\n\rCS_LEAVE_ROOM\x10\x04\x12\x0b\n\x07\x43S_CHAT\x10\x05\x12\x0f\n\x0b\x43S_SHUTDOWN\x10\x06\x12\x13\n\x0fSC_ROOMS_RESULT\x10\x07\x12\x0b\n\x07SC_CHAT\x10\x08\x12\x15\n\x11SC_SYSTEM_MESSAGE\x10\t\"\x16\n\x06\x43SName\x12\x0c\n\x04name\x18\x01 \x02(\t\"\t\n\x07\x43SRooms\"\x1d\n\x0c\x43SCreateRoom\x12\r\n\x05title\x18\x01 \x01(\t\"\x1c\n\nCSJoinRoom\x12\x0e\n\x06roomId\x18\x01 \x02(\x05\"\r\n\x0b\x43SLeaveRoom\"\x16\n\x06\x43SChat\x12\x0c\n\x04text\x18\x01 \x02(\t\"\x0c\n\nCSShutdown\"\x1d\n\x0cSCNameResult\x12\r\n\x05\x65rror\x18\x01 \x01(\t\"w\n\rSCRoomsResult\x12*\n\x05rooms\x18\x01 \x03(\x0b\x32\x1b.mju.SCRoomsResult.RoomInfo\x1a:\n\x08RoomInfo\x12\x0e\n\x06roomId\x18\x01 \x02(\x05\x12\r\n\x05title\x18\x02 \x01(\t\x12\x0f\n\x07members\x18\x03 \x03(\t\"#\n\x12SCCreateRoomResult\x12\r\n\x05\x65rror\x18\x01 \x01(\t\"!\n\x10SCJoinRoomResult\x12\r\n\x05\x65rror\x18\x01 \x01(\t\"\"\n\x11SCLeaveRoomResult\x12\r\n\x05\x65rror\x18\x01 \x01(\t\"&\n\x06SCChat\x12\x0e\n\x06member\x18\x01 \x02(\t\x12\x0c\n\x04text\x18\x02 \x02(\t\"\x1f\n\x0fSCSystemMessage\x12\x0c\n\x04text\x18\x01 \x02(\t')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'message_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _TYPE._serialized_start=23
  _TYPE._serialized_end=253
  _TYPE_MESSAGETYPE._serialized_start=69
  _TYPE_MESSAGETYPE._serialized_end=253
  _CSNAME._serialized_start=255
  _CSNAME._serialized_end=277
  _CSROOMS._serialized_start=279
  _CSROOMS._serialized_end=288
  _CSCREATEROOM._serialized_start=290
  _CSCREATEROOM._serialized_end=319
  _CSJOINROOM._serialized_start=321
  _CSJOINROOM._serialized_end=349
  _CSLEAVEROOM._serialized_start=351
  _CSLEAVEROOM._serialized_end=364
  _CSCHAT._serialized_start=366
  _CSCHAT._serialized_end=388
  _CSSHUTDOWN._serialized_start=390
  _CSSHUTDOWN._serialized_end=402
  _SCNAMERESULT._serialized_start=404
  _SCNAMERESULT._serialized_end=433
  _SCROOMSRESULT._serialized_start=435
  _SCROOMSRESULT._serialized_end=554
  _SCROOMSRESULT_ROOMINFO._serialized_start=496
  _SCROOMSRESULT_ROOMINFO._serialized_end=554
  _SCCREATEROOMRESULT._serialized_start=556
  _SCCREATEROOMRESULT._serialized_end=591
  _SCJOINROOMRESULT._serialized_start=593
  _SCJOINROOMRESULT._serialized_end=626
  _SCLEAVEROOMRESULT._serialized_start=628
  _SCLEAVEROOMRESULT._serialized_end=662
  _SCCHAT._serialized_start=664
  _SCCHAT._serialized_end=702
  _SCSYSTEMMESSAGE._serialized_start=704
  _SCSYSTEMMESSAGE._serialized_end=735
# @@protoc_insertion_point(module_scope)