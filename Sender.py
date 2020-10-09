import socket
import sys
import _thread
import time
import string
import packet
import udt
import random
from functools import partial
from timer import Timer

# Some already defined parameters
PACKET_SIZE = 512
RECEIVER_ADDR = ('localhost', 8080)
SENDER_ADDR = ('localhost', 9090)
SLEEP_INTERVAL = 2.0 # (In seconds)
TIMEOUT_INTERVAL = 1.0
WINDOW_SIZE = 4
RETRY_ATTEMPTS = 20

# You can use some shared resources over the two threads
mutex = _thread.allocate_lock()
timer = Timer(TIMEOUT_INTERVAL)
pkt_buffer = []
# Need to have two threads: one for sending and another for receiving ACKs
sync  = False
alive = True


# Generate random payload of any length
def generate_payload(length=10):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))

    return result_str


# Send using Stop_n_wait protocol
def send_snw(sock):
    # Access to shared resources
    global switch
    # Track packet count
    seq = 0

    # Open file as read
    with open(filename, "r") as f:
        # iterate through file at increments of packet size
        for p in iter(partial(f.read, PACKET_SIZE), b''):
            # Lock packet transfer
            with mutex:

                # Generate Packet & Link Buffer
                data = p.encode()
                pkt = packet.make(seq, data)
                pkt_buffer.append(pkt)

                # Handle Thread Timing
                switch = True

                # Send Packet and Increment Sequence
                print("Sending seq# ", seq, "\n")
                udt.send(pkt, sock, RECEIVER_ADDR)
                seq += 1

            # Delay Mutex for sister thread
            time.sleep(SLEEP_INTERVAL)
            if not p:
                break
        # Prepare & Send END packet
        with mutex:
            pkt = packet.make(seq, "END".encode())
            pkt_buffer.append(pkt)
            udt.send(pkt, sock, RECEIVER_ADDR)


# Send using GBN protocol
def send_gbn(sock):
    global base, timer, mutex
    packetStore = []
    packetSeq = 0
    try:
        file = open("bio.txt", "r") # reads bio.txt file
        data = ' '
        while data:
            data = file.read(PACKET_SIZE)  # makes the packets
            packetStore.append(packet.make(packetStore, data)) # stores packets in packet list
            packetSeq += 1 # updates packet sequence counter

        base = 0
        window = WINDOW_SIZE
        packetSeq = 0

        # Starting a new thread
        _thread.start_new_thread(receive_gbn(sock))

        while base < len(packetStore):
            mutex.acquire()

            if not timer.running():
                timer.start()

            while packetSeq < len(packetStore) & packetSeq < base + window:
                print("\nSending Packet Sequence #:", packetSeq)
                udt.send(packetStore[packetSeq], sock, RECEIVER_ADDR)

            while not timer.timeout() and timer.running():
                print("Sleeping")
                mutex.release()
                time.sleep(SLEEP_INTERVAL)
                mutex.acquire()

            mutex.release()

            if not timer.timeout():
                window = min((len(packetStore)-base), WINDOW_SIZE)
            else:
                print("\nTimeout occurred")
                timer.stop()
                packetSeq = base

        lastPacket = packet.make(packetSeq, "End".encode())
        udt.send(lastPacket, sock, RECEIVER_ADDR)
        file.close()

    except IOError:
        print(IOError)
        return


# Receive thread for stop-n-wait
def receive_snw(sock, pkt):
    # Shared Resource Access
    global switch, alive

    # Spin lock to synchronize execution
    while not switch:
        continue

    # While Packets still exist
    while pkt_buffer:
        # acuire thread lock
        mutex.acquire()
        # print if lock was aquired
        print("Acquired")
        # Retry Delay
        timer.start()
        # Get Packet
        p = pkt.pop()

        # R
        retry = RETRY_ATTEMPTS
        while retry:
            try:
                # Try ACK Check
                ack, recvaddr = udt.recv(sock)
                print("Receiver address: ", recvaddr, "ack", ack)
                # If received, cleanup and pass baton
                timer.stop()
                mutex.release()
                time.sleep(SLEEP_INTERVAL)
                retry = RETRY_ATTEMPTS
                break

            except BlockingIOError:

                # Otherwise, check timer and restart
                if timer.timeout():
                    retry -= 1
                    udt.send(p, sock, RECEIVER_ADDR)
                    timer.start()
    alive = False


# Receive thread for GBN
def receive_gbn(sock):
    global base, timer, mutex
    end = ''
    try:

        while end != 'END':
            pckt, sendAddr = udt.recv(sock)
            packetSeq, data = packet.extract(pckt)
            end = data.decode()

            print("\nPacket From: ", SENDER_ADDR, ", Seq# ", packetSeq, end)

            if base <= packetSeq:
                mutex.acquire()
                base = packetSeq + 1
                timer.stop()
                mutex.release()

    except IOError:
        print(IOError)
        return


# Main function
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Expected filename as command line argument')
        exit()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    sock.bind(SENDER_ADDR)

    filename = sys.argv[1]

    _thread.start_new_thread(send_snw, (sock,))
    time.sleep(1)
    _thread.start_new_thread(receive_snw, (sock, pkt_buffer))

    while alive:
        continue

    sock.close()
