"""
State management for P2P client
"""
import threading
from typing import Dict, Optional
from models import PeerInfo, ConnectionInfo
from datetime import datetime


class PeerState:
    """Thread-safe state management for peers"""
    
    def __init__(self):
        self._peers: Dict[str, PeerInfo] = {}
        self._connections: Dict[str, ConnectionInfo] = {}
        self._lock = threading.RLock()
    
    def add_peer(self, peer: PeerInfo):
        """Add or update peer information"""
        with self._lock:
            self._peers[peer.peer_id] = peer
    
    def get_peer(self, peer_id: str) -> Optional[PeerInfo]:
        """Get peer information"""
        with self._lock:
            return self._peers.get(peer_id)
    
    def remove_peer(self, peer_id: str):
        """Remove peer from state"""
        with self._lock:
            self._peers.pop(peer_id, None)
    
    def get_all_peers(self) -> Dict[str, PeerInfo]:
        """Get all peers"""
        with self._lock:
            return self._peers.copy()
    
    def get_peers_by_namespace(self, namespace: str) -> Dict[str, PeerInfo]:
        """Get all peers in a namespace"""
        with self._lock:
            return {
                peer_id: peer 
                for peer_id, peer in self._peers.items() 
                if peer.namespace == namespace
            }
    
    def add_connection(self, conn: ConnectionInfo):
        """Add connection information"""
        with self._lock:
            self._connections[conn.peer_id] = conn
    
    def get_connection(self, peer_id: str) -> Optional[ConnectionInfo]:
        """Get connection information"""
        with self._lock:
            return self._connections.get(peer_id)
    
    def remove_connection(self, peer_id: str):
        """Remove connection"""
        with self._lock:
            self._connections.pop(peer_id, None)
    
    def get_all_connections(self) -> Dict[str, ConnectionInfo]:
        """Get all connections"""
        with self._lock:
            return self._connections.copy()
    
    def update_peer_rtt(self, peer_id: str, rtt: float):
        """Update peer RTT"""
        with self._lock:
            peer = self._peers.get(peer_id)
            if peer:
                peer.add_rtt_sample(rtt)
                peer.last_seen = datetime.now()
    
    def clear(self):
        """Clear all state"""
        with self._lock:
            self._peers.clear()
            self._connections.clear()
