"""
Interface de linha de comando para o Cliente de Chat P2P
"""
import logging
import threading
import sys
from typing import Callable

logger = logging.getLogger(__name__)


class CLI:
    """Manipulador da interface de linha de comando"""
    
    def __init__(self, 
                 on_peers: Callable[[str], None],
                 on_msg: Callable[[str, str], None],
                 on_pub: Callable[[str, str], None],
                 on_conn: Callable[[], None],
                 on_rtt: Callable[[], None],
                 on_reconnect: Callable[[], None],
                 on_log: Callable[[str], None],
                 on_quit: Callable[[], None],
                 on_relay: Callable[[str, str], None] = None):
        self.on_peers = on_peers
        self.on_msg = on_msg
        self.on_pub = on_pub
        self.on_conn = on_conn
        self.on_rtt = on_rtt
        self.on_reconnect = on_reconnect
        self.on_log = on_log
        self.on_quit = on_quit
        self.on_relay = on_relay
        self.running = False
        self.input_thread = None
    
    def start(self):
        """Inicia a thread de entrada da CLI"""
        self.running = True
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
        self.print_help()
    
    def stop(self):
        """Para a CLI"""
        self.running = False
    
    def print_help(self):
        """Exibe os comandos disponíveis"""
        print("\n" + "="*60)
        print("P2P Chat Client - Available Commands:")
        print("="*60)
        print("/peers [* | #namespace]  - Discover and list peers")
        print("/msg <peer_id> <message> - Send direct message (auto-relay if needed)")
        print("/relay <peer_id> <msg>   - Force send via relay")
        print("/pub * <message>         - Broadcast to all peers")
        print("/pub #<namespace> <msg>  - Send to namespace")
        print("/conn                    - Show active connections")
        print("/rtt                     - Show RTT statistics")
        print("/reconnect               - Force reconnection")
        print("/log <LEVEL>             - Set log level (DEBUG, INFO, WARNING, ERROR)")
        print("/quit                    - Exit application")
        print("/help                    - Show this help")
        print("="*60 + "\n")
    
    def _input_loop(self):
        """Lê e processa entrada do usuário"""
        while self.running:
            try:
                line = input()
                if not line:
                    continue
                
                line = line.strip()
                if not line.startswith('/'):
                    print("Commands must start with '/'. Type /help for available commands.")
                    continue
                
                self._process_command(line)
                
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nUse /quit to exit")
            except Exception as e:
                logger.error(f"Error processing input: {e}")
    
    def _process_command(self, line: str):
        """Processa um comando"""
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        try:
            if cmd == "/help":
                self.print_help()
            
            elif cmd == "/peers":
                scope = args if args else "*"
                self.on_peers(scope)
            
            elif cmd == "/msg":
                if not args:
                    print("Usage: /msg <peer_id> <message>")
                    return
                
                parts = args.split(None, 1)
                if len(parts) < 2:
                    print("Usage: /msg <peer_id> <message>")
                    return
                
                peer_id, message = parts
                self.on_msg(peer_id, message)
            
            elif cmd == "/pub":
                if not args:
                    print("Usage: /pub <* | #namespace> <message>")
                    return
                
                parts = args.split(None, 1)
                if len(parts) < 2:
                    print("Usage: /pub <* | #namespace> <message>")
                    return
                
                scope, message = parts
                if scope not in ["*"] and not scope.startswith("#"):
                    print("Scope must be '*' or '#namespace'")
                    return
                
                self.on_pub(scope, message)
            
            elif cmd == "/conn":
                self.on_conn()
            
            elif cmd == "/rtt":
                self.on_rtt()
            
            elif cmd == "/reconnect":
                self.on_reconnect()
            
            elif cmd == "/relay":
                if not args:
                    print("Usage: /relay <peer_id> <message>")
                    return
                
                parts = args.split(None, 1)
                if len(parts) < 2:
                    print("Usage: /relay <peer_id> <message>")
                    return
                
                peer_id, message = parts
                if self.on_relay:
                    self.on_relay(peer_id, message)
                else:
                    print("Relay not available")
            
            elif cmd == "/log":
                if not args:
                    print("Usage: /log <LEVEL> (DEBUG, INFO, WARNING, ERROR)")
                    return
                self.on_log(args.upper())
            
            elif cmd == "/quit":
                self.on_quit()
            
            else:
                print(f"Unknown command: {cmd}. Type /help for available commands.")
        
        except Exception as e:
            logger.error(f"Error executing command '{cmd}': {e}")
            print(f"Error: {e}")
