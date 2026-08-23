"""
AuraTool-Suite — Chat Rooms Module
===================================
Provides real-time chat room infrastructure for technicians, workshop staff,
and customer support communication.
"""

import datetime
import logging
import uuid


class ChatMessage:
    def __init__(self, sender: str, content: str, room_id: str = "general"):
        self.msg_id = str(uuid.uuid4())[:8]
        self.sender = sender
        self.content = content
        self.room_id = room_id
        self.timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    def to_dict(self) -> dict:
        return {
            "msg_id": self.msg_id,
            "sender": self.sender,
            "content": self.content,
            "room_id": self.room_id,
            "timestamp": self.timestamp,
        }


class ChatRoomManager:
    """Manages multi-channel technician chat rooms and support threads."""

    DEFAULT_ROOMS = ["general", "technicians", "firmware_help", "hardware_repairs"]

    def __init__(self):
        self.logger = logging.getLogger("AuraTool.ChatRooms")
        self.rooms = {room: [] for room in self.DEFAULT_ROOMS}
        self.active_users = {"Technician_Admin", "Support_Bot"}

    def join_room(self, username: str, room_id: str) -> bool:
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        self.active_users.add(username)
        self.logger.info(f"User '{username}' joined chat room '{room_id}'.")
        return True

    def send_message(self, sender: str, room_id: str, content: str) -> ChatMessage:
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        msg = ChatMessage(sender, content, room_id)
        self.rooms[room_id].append(msg)
        self.logger.info(f"[{room_id}] {sender}: {content}")
        return msg

    def get_messages(self, room_id: str, limit: int = 50) -> list[dict]:
        messages = self.rooms.get(room_id, [])
        return [m.to_dict() for m in messages[-limit:]]

    def create_room(self, room_id: str) -> bool:
        if room_id not in self.rooms:
            self.rooms[room_id] = []
            self.logger.info(f"Created new chat room: '{room_id}'.")
            return True
        return False
