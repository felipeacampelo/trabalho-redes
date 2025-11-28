"""
Message routing and delivery
"""
import logging
import uuid
import threading
import time
from typing import Dict, Callable, Optional
from datetime import datetime
from models import Message, MessageType

logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes messages to appropriate peers"""
    
    def __init__(self, my_peer_id: str, send_message: Callable[[str, Message], bool],
                 get_connected_peers: Callable[[], list],
                 get_peers_by_namespace: Callable[[str], list],
                 ack_timeout: int = 5):
        self.my_peer_id = my_peer_id
        self.send_message = send_message
        self.get_connected_peers = get_connected_peers
        self.get_peers_by_namespace = get_peers_by_namespace
        self.ack_timeout = ack_timeout
        self.pending_acks: Dict[str, Dict[str, datetime]] = {}  # peer_id -> {msg_id -> timestamp}
        self.lock = threading.Lock()
        self.running = False
        self.timeout_thread = None
    
    def start(self):
        """Start message router"""
        self.running = True
        self.timeout_thread = threading.Thread(target=self._check_ack_timeouts, daemon=True)
        self.timeout_thread.start()
        logger.info("[Router] Started")
    
    def stop(self):
        """Stop message router"""
        self.running = False
        if self.timeout_thread:
            self.timeout_thread.join(timeout=2)
    
    def send_direct(self, dst_peer_id: str, payload: str, require_ack: bool = True) -> bool:
        """Send direct message to a peer"""
        msg_id = str(uuid.uuid4())
        message = Message(
            msg_type=MessageType.SEND,
            msg_id=msg_id,
            src=self.my_peer_id,
            dst=dst_peer_id,
            payload=payload,
            require_ack=require_ack
        )
        
        if require_ack:
            with self.lock:
                if dst_peer_id not in self.pending_acks:
                    self.pending_acks[dst_peer_id] = {}
                self.pending_acks[dst_peer_id][msg_id] = datetime.now()
        
        success = self.send_message(dst_peer_id, message)
        if success:
            logger.info(f"[Router] SEND {dst_peer_id}: {payload}")
        else:
            logger.error(f"[Router] Failed to send to {dst_peer_id}")
            with self.lock:
                if dst_peer_id in self.pending_acks:
                    self.pending_acks[dst_peer_id].pop(msg_id, None)
        
        return success
    
    def publish(self, scope: str, payload: str) -> int:
        """
        Publish message to a scope
        scope can be:
        - '*' for broadcast to all connected peers
        - '#namespace' for all peers in a namespace
        """
        msg_id = str(uuid.uuid4())
        
        # Determine target peers
        if scope == "*":
            target_peers = self.get_connected_peers()
            logger.info(f"[Router] PUB * (broadcast): {payload}")
        elif scope.startswith("#"):
            namespace = scope[1:]
            target_peers = self.get_peers_by_namespace(namespace)
            logger.info(f"[Router] PUB {scope}: {payload}")
        else:
            logger.error(f"[Router] Invalid scope: {scope}")
            return 0
        
        # Send to all target peers
        sent_count = 0
        for peer_id in target_peers:
            message = Message(
                msg_type=MessageType.PUB,
                msg_id=msg_id,
                src=self.my_peer_id,
                dst=scope,
                payload=payload,
                require_ack=False
            )
            
            if self.send_message(peer_id, message):
                sent_count += 1
        
        logger.info(f"[Router] Published to {sent_count}/{len(target_peers)} peers")
        return sent_count
    
    def handle_ack(self, peer_id: str, msg_id: str):
        """Handle ACK for a sent message"""
        with self.lock:
            if peer_id in self.pending_acks and msg_id in self.pending_acks[peer_id]:
                sent_time = self.pending_acks[peer_id][msg_id]
                rtt = (datetime.now() - sent_time).total_seconds() * 1000
                del self.pending_acks[peer_id][msg_id]
                logger.debug(f"[Router] ACK from {peer_id} for {msg_id}, RTT: {rtt:.2f} ms")
    
    def send_ack(self, peer_id: str, msg_id: str) -> bool:
        """Send ACK for a received message"""
        ack = Message(
            msg_type=MessageType.ACK,
            msg_id=msg_id,
            timestamp=datetime.now().isoformat()
        )
        return self.send_message(peer_id, ack)
    
    def _check_ack_timeouts(self):
        """Check for ACK timeouts"""
        while self.running:
            try:
                time.sleep(1)
                now = datetime.now()
                
                with self.lock:
                    for peer_id, acks in list(self.pending_acks.items()):
                        for msg_id, sent_time in list(acks.items()):
                            elapsed = (now - sent_time).total_seconds()
                            if elapsed > self.ack_timeout:
                                logger.warning(f"[Router] ACK timeout for message {msg_id} to {peer_id}")
                                del acks[msg_id]
                        
                        if not acks:
                            del self.pending_acks[peer_id]
            
            except Exception as e:
                logger.error(f"[Router] Error checking ACK timeouts: {e}")
    
    def clear_peer(self, peer_id: str):
        """Clear pending ACKs for a peer"""
        with self.lock:
            self.pending_acks.pop(peer_id, None)
