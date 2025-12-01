#!/bin/bash
# Test script to launch multiple P2P clients

echo "Starting P2P Chat Client Test"
echo "=============================="
echo ""
echo "This script will launch 3 clients in separate terminals:"
echo "  - felipe@CIC on port 4001"
echo "  - joao@CIC on port 4002"
echo "  - teste@CIC on port 4003"
echo ""
echo "Press Enter to continue..."
read

# Check if we're on macOS or Linux  
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    osascript -e 'tell app "Terminal" to do script "cd \"'$(pwd)'\" && python3 main.py --name alice --port 4001"'
    sleep 1
    osascript -e 'tell app "Terminal" to do script "cd \"'$(pwd)'\" && python3 main.py --name bob --port 4002"'
    sleep 1
    osascript -e 'tell app "Terminal" to do script "cd \"'$(pwd)'\" && python3 main.py --name charlie --port 4003"'
else
    # Linux
    gnome-terminal -- bash -c "python3 main.py --name alice --port 4001; exec bash"
    sleep 1
    gnome-terminal -- bash -c "python3 main.py --name bob --port 4002; exec bash"
    sleep 1
    gnome-terminal -- bash -c "python3 main.py --name charlie --port 4003; exec bash"
fi

echo ""
echo "Clients launched!"
echo ""
echo "Try these commands in each terminal:"
echo "  /peers *           - List all peers"
echo "  /msg bob@CIC hi    - Send message to bob"
echo "  /pub * hello all   - Broadcast to everyone"
echo "  /conn              - Show connections"
echo "  /rtt               - Show RTT stats"
echo "  /quit              - Exit"
