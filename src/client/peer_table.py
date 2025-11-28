"""
Peer table management with reconnection logic
"""
import logging
import threading
import time
from typing import Dict, Callable
from models import PeerInfo, PeerStatus

logger = logging.getLogger(__name__)


class PeerTable:
    """
    Manages peer discovery, connection state, and reconnection logic
    """
    
    def __init__(self, max_reconnect_attempts: int, backoff_base: int, backoff_max: int,
                 connect_to_peer: Callable[[PeerInfo], bool]):
        self.max_reconnect_attempts = max_reconnect_attempts
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.connect_to_peer = connect_to_peer
        self.peers: Dict[str, PeerInfo] = {}
        self.lock = threading.RLock()
        self.running = False
        self.reconnect_thread = None
    
    def start(self):
        """Start reconnection thread"""
        self.running = True
        self.reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self.reconnect_thread.start()
        logger.info("[PeerTable] Started")
    
    def stop(self):
        """Stop reconnection thread"""
        self.running = False
        if self.reconnect_thread:
            self.reconnect_thread.join(timeout=2)
    
    def update_peers(self, discovered_peers: list, my_peer_id: str):
        """Update peer table with discovered peers"""
        with self.lock:
            current_peer_ids = set(self.peers.keys())
            discovered_peer_ids = set()
            
            for peer_data in discovered_peers:
                peer_id = f"{peer_data['name']}@{peer_data['namespace']}"
                
                # Skip self
                if peer_id == my_peer_id:
                    continue
                
                discovered_peer_ids.add(peer_id)
                
                if peer_id in self.peers:
                    # Update existing peer
                    peer = self.peers[peer_id]
                    peer.ip = peer_data['ip']
                    peer.port = peer_data['port']
                    
                    # If peer was stale, mark as disconnected to retry
                    if peer.status == PeerStatus.STALE:
                        peer.status = PeerStatus.DISCONNECTED
                        peer.reconnect_attempts = 0
                else:
                    # New peer
                    peer = PeerInfo(
                        peer_id=peer_id,
                        ip=peer_data['ip'],
                        port=peer_data['port'],
                        namespace=peer_data['namespace'],
                        name=peer_data['name'],
                        status=PeerStatus.DISCONNECTED
                    )
                    self.peers[peer_id] = peer
                    logger.info(f"[PeerTable] New peer discovered: {peer_id}")
            
            # Mark peers that disappeared as stale
            disappeared = current_peer_ids - discovered_peer_ids
            for peer_id in disappeared:
                if self.peers[peer_id].status != PeerStatus.CONNECTED:
                    self.peers[peer_id].status = PeerStatus.STALE
                    logger.info(f"[PeerTable] Peer marked as stale: {peer_id}")
    
    def mark_connected(self, peer_id: str):
        """Mark peer as connected"""
        with self.lock:
            if peer_id in self.peers:
                self.peers[peer_id].status = PeerStatus.CONNECTED
                self.peers[peer_id].reconnect_attempts = 0
                logger.info(f"[PeerTable] Peer connected: {peer_id}")
    
    def mark_disconnected(self, peer_id: str):
        """Mark peer as disconnected"""
        with self.lock:
            if peer_id in self.peers:
                self.peers[peer_id].status = PeerStatus.DISCONNECTED
                logger.info(f"[PeerTable] Peer disconnected: {peer_id}")
    
    def get_peer(self, peer_id: str) -> PeerInfo:
        """Get peer info"""
        with self.lock:
            return self.peers.get(peer_id)
    
    def get_all_peers(self) -> Dict[str, PeerInfo]:
        """Get all peers"""
        with self.lock:
            return self.peers.copy()
    
    def get_connected_peers(self) -> list:
        """Get list of connected peer IDs"""
        with self.lock:
            return [
                peer_id for peer_id, peer in self.peers.items()
                if peer.status == PeerStatus.CONNECTED
            ]
    
    def get_peers_by_namespace(self, namespace: str) -> list:
        """Get connected peers in a namespace"""
        with self.lock:
            return [
                peer_id for peer_id, peer in self.peers.items()
                if peer.namespace == namespace and peer.status == PeerStatus.CONNECTED
            ]
    
    def force_reconnect(self):
        """Force reconnection attempt for all disconnected peers"""
        with self.lock:
            for peer in self.peers.values():
                if peer.status == PeerStatus.DISCONNECTED:
                    peer.reconnect_attempts = 0
        logger.info("[PeerTable] Forced reconnection for all disconnected peers")
    
    def _reconnect_loop(self):
        """Periodically attempt to reconnect to disconnected peers"""
        while self.running:
            try:
                time.sleep(5)  # Check every 5 seconds
                
                with self.lock:
                    for peer_id, peer in list(self.peers.items()):
                        if peer.status == PeerStatus.DISCONNECTED:
                            # Check if we should attempt reconnection
                            if peer.reconnect_attempts < self.max_reconnect_attempts:
                                # Calculate backoff
                                backoff = min(
                                    self.backoff_base ** peer.reconnect_attempts,
                                    self.backoff_max
                                )
                                
                                # Simple check: just try to reconnect
                                # In a real implementation, you'd track last attempt time
                                logger.info(f"[PeerTable] Attempting to reconnect to {peer_id} "
                                          f"(attempt {peer.reconnect_attempts + 1}/{self.max_reconnect_attempts})")
                                
                                peer.status = PeerStatus.CONNECTING
                                peer.reconnect_attempts += 1
                                
                                # Try to connect (this will be handled by parent)
                                success = self.connect_to_peer(peer)
                                
                                if not success:
                                    peer.status = PeerStatus.DISCONNECTED
                            
                            elif peer.reconnect_attempts >= self.max_reconnect_attempts:
                                # Give up
                                peer.status = PeerStatus.STALE
                                logger.warning(f"[PeerTable] Giving up on {peer_id} after "
                                             f"{self.max_reconnect_attempts} attempts")
            
            except Exception as e:
                logger.error(f"[PeerTable] Error in reconnect loop: {e}")
