"""
Modelos de dados para o Cliente de Chat P2P
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PeerStatus(Enum):
    """Status de conexão do peer"""
    UNKNOWN = "unknown"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    STALE = "stale"


class MessageType(Enum):
    """Tipos de mensagem para o protocolo P2P"""
    HELLO = "HELLO"
    HELLO_OK = "HELLO_OK"
    PING = "PING"
    PONG = "PONG"
    SEND = "SEND"
    ACK = "ACK"
    PUB = "PUB"
    BYE = "BYE"
    BYE_OK = "BYE_OK"
    RELAY = "RELAY"  # Para retransmitir mensagens através de peers intermediários


@dataclass
class PeerInfo:
    """Informações sobre um peer"""
    peer_id: str
    ip: str
    port: int
    namespace: str
    name: str
    status: PeerStatus = PeerStatus.UNKNOWN
    last_seen: Optional[datetime] = None
    reconnect_attempts: int = 0
    rtt_samples: List[float] = field(default_factory=list)
    
    @property
    def avg_rtt(self) -> Optional[float]:
        """Calcula o RTT médio"""
        if not self.rtt_samples:
            return None
        return sum(self.rtt_samples) / len(self.rtt_samples)
    
    def add_rtt_sample(self, rtt: float):
        """Adiciona amostra de RTT, mantém as últimas 10"""
        self.rtt_samples.append(rtt)
        if len(self.rtt_samples) > 10:
            self.rtt_samples.pop(0)


@dataclass
class Message:
    """Estrutura de mensagem P2P"""
    msg_type: MessageType
    msg_id: str
    src: Optional[str] = None
    dst: Optional[str] = None
    payload: Optional[str] = None
    timestamp: Optional[str] = None
    ttl: int = 1
    require_ack: bool = False
    version: Optional[str] = None
    features: Optional[List[str]] = None
    reason: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Converte mensagem para dicionário para serialização JSON"""
        data = {"type": self.msg_type.value, "ttl": self.ttl}
        
        if self.msg_id:
            data["msg_id"] = self.msg_id
        if self.src:
            data["src"] = self.src
        if self.dst:
            data["dst"] = self.dst
        if self.payload is not None:
            data["payload"] = self.payload
        if self.timestamp:
            data["timestamp"] = self.timestamp
        if self.require_ack:
            data["require_ack"] = self.require_ack
        if self.version:
            data["version"] = self.version
            data["peer_id"] = self.src
        if self.features:
            data["features"] = self.features
        if self.reason:
            data["reason"] = self.reason
            
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        """Cria mensagem a partir de dicionário"""
        msg_type = MessageType(data.get("type"))
        return cls(
            msg_type=msg_type,
            msg_id=data.get("msg_id", ""),
            src=data.get("src") or data.get("peer_id"),
            dst=data.get("dst"),
            payload=data.get("payload"),
            timestamp=data.get("timestamp"),
            ttl=data.get("ttl", 1),
            require_ack=data.get("require_ack", False),
            version=data.get("version"),
            features=data.get("features"),
            reason=data.get("reason")
        )


@dataclass
class ConnectionInfo:
    """Informações sobre uma conexão"""
    peer_id: str
    direction: str  # "inbound" (entrada) ou "outbound" (saída)
    connected_at: datetime
    last_ping: Optional[datetime] = None
    last_pong: Optional[datetime] = None
