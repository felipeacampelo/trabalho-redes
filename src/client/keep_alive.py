"""
Keep-alive mechanism for peer connections
"""
import threading
import time
import logging
import uuid
from typing import Dict, Callable
from datetime import datetime
from models import Message, MessageType

logger = logging.getLogger(__name__)


class KeepAlive:
    """Manages PING/PONG keep-alive for all peer connections"""
    
    def __init__(self, ping_interval: int, send_message: Callable[[str, Message], bool]):
        self.ping_interval = ping_interval
        self.send_message = send_message
        self.running = False
        self.thread = None
        self.pending_pings: Dict[str, Dict[str, datetime]] = {}  # peer_id -> {msg_id -> timestamp}
        self.lock = threading.Lock()
    
    def start(self):
        """Start keep-alive thread"""
        self.running = True
        self.thread = threading.Thread(target=self._keep_alive_loop, daemon=True)
        self.thread.start()
        logger.info("[KeepAlive] Started")
    
    def stop(self):
        """Stop keep-alive thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def handle_pong(self, peer_id: str, msg_id: str, on_rtt: Callable[[str, float], None]):
        """Handle PONG response and calculate RTT"""
        with self.lock:
            if peer_id in self.pending_pings and msg_id in self.pending_pings[peer_id]:
                sent_time = self.pending_pings[peer_id][msg_id]
                rtt = (datetime.now() - sent_time).total_seconds() * 1000  # ms
                del self.pending_pings[peer_id][msg_id]
                
                logger.debug(f"[KeepAlive] PONG from {peer_id}, RTT: {rtt:.2f} ms")
                on_rtt(peer_id, rtt)
    
    def _keep_alive_loop(self):
        """Send periodic PINGs to all connected peers"""
        while self.running:
            try:
                time.sleep(self.ping_interval)
                
                # Get list of peers to ping (this should be provided by parent)
                # For now, we'll ping all peers with pending connections
                self._send_pings()
                
            except Exception as e:
                logger.error(f"[KeepAlive] Error in keep-alive loop: {e}")
    
    def _send_pings(self):
        """Send PING to all connected peers"""
        # This will be called by the parent with the list of peer_ids
        pass
    
    def send_ping(self, peer_id: str) -> bool:
        """Send PING to a specific peer"""
        msg_id = str(uuid.uuid4())
        ping = Message(
            msg_type=MessageType.PING,
            msg_id=msg_id,
            timestamp=datetime.now().isoformat()
        )
        
        with self.lock:
            if peer_id not in self.pending_pings:
                self.pending_pings[peer_id] = {}
            self.pending_pings[peer_id][msg_id] = datetime.now()
        
        success = self.send_message(peer_id, ping)
        if not success:
            with self.lock:
                if peer_id in self.pending_pings:
                    self.pending_pings[peer_id].pop(msg_id, None)
        
        return success
    
    def clear_peer(self, peer_id: str):
        """Clear pending pings for a peer"""
        with self.lock:
            self.pending_pings.pop(peer_id, None)
