  # receiver.py - The receiver in the reliable data transer protocol
import packet
import socket
import sys
import udt

RECEIVER_ADDR = ('localhost', 8080)

# Receive packets from the sender w/ GBN protocol
def receive_gbn(sock):
    end = ""
    packetSeq = 0
    sock.settimeout(10)
    try:
        receivedData = open("receivedData.txt", "a")
        while end != "END":
            try:
                pcket, senderAddress = udt.recv(sock)
            except socket.timeout():
                print("Time out")
                break
            seq, packetData = packet.extract(pcket)
            print("Packet received: ", seq)
            print("Packet Data: ", packetData)

            if packetSeq != seq:
                print("Ack: ", packetSeq -1)
                pcket = packet.make(packetSeq-1)
                udt.send(pcket, sock, senderAddress)

            else:
                end = packetData.decode()
                pcket = packet.make(packetSeq)
                udt.send(pcket, sock, senderAddress)
                receivedData.write(end)
                packetSeq += 1

    except IOError:
        print(IOError)
        return


# Receive packets from the sender w/ SR protocol
def receive_sr(sock, windowsize):
    # Fill here
    return


# Receive packets from the sender w/ Stop-n-wait protocol
def receive_snw(sock):
    endStr = ''
    _seq = -1
    while endStr != 'END':
        pkt, senderaddr = udt.recv(sock)
        seq, data = packet.extract(pkt)
        if _seq != seq:
            _seq = seq
            endStr = data.decode()
            print("From: ", senderaddr, ", Seq# ", seq, endStr)
        udt.send(b' ', sock, ('localhost', 9090))


  # Main function
if __name__ == '__main__':
    # if len(sys.argv) != 2:
    #     print('Expected filename as command line argument')
    #     exit()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(RECEIVER_ADDR)
    # filename = sys.argv[1]
    receive_snw(sock)

    # Close the socket
    sock.close()