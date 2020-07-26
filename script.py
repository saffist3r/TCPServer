import socket, select
from datetime import datetime
#Commands
EOL = b'QUIT'
DATE = b'DATE'
EHLO = b'EHLO'

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serversocket.bind(('0.0.0.0', 4242)) #Open a localhost socket and Bind it with the 4242 port.
serversocket.listen(1) #One second delay
serversocket.setblocking(0) #Since we are using EPOLL, we need a non-Blocking Socket Server.

epoll = select.epoll()
epoll.register(serversocket.fileno(), select.EPOLLIN)

try:
    connections = {};
    requests = {};
    responses = {}
    while True:
        events = epoll.poll(1)
        for fileno, event in events:
            if fileno == serversocket.fileno():
                connection, address = serversocket.accept()
                connection.setblocking(0)
                epoll.register(connection.fileno(), select.EPOLLIN)
                connections[connection.fileno()] = connection
                requests[connection.fileno()] = b''
                responses[connection.fileno()] = b''
            elif event & select.EPOLLIN:  # if a POLLIN event is detected.
                latestReq = connections[fileno].recv(1024) #Read the data
                requests[fileno] += latestReq
                print(requests[fileno]) #Print the command for debug purpose.
                if DATE in latestReq:
                    if EHLO in requests[fileno]:
                        responses[fileno] += datetime.now().strftime(
                            "%d/%m/%YT%H:%M:%S").encode()  # JJ/MM/AAAATHH:mm:ss
                        responses[fileno] += b'\n'
                    else:
                        responses[fileno] += b'550 BAD STATE\n'
                    epoll.modify(fileno, select.EPOLLOUT)
                elif EOL in latestReq:
                    responses[fileno] += b'221 Bye\n'
                    epoll.modify(fileno, select.EPOLLOUT)
                elif EHLO in latestReq:
                    stringToPrint = '250 Pleased to meet you' + latestReq.decode().replace('EHLO ', ' ')
                    responses[fileno] += stringToPrint.encode()
                    epoll.modify(fileno, select.EPOLLOUT)

            elif event & select.EPOLLOUT:  # if a pullout event is detected.
                connections[fileno].send(responses[fileno])
                responses[fileno] = b'' #reset the repsponses Array.
                if EOL in requests[fileno]:
                    epoll.modify(fileno, 0)
                    connections[fileno].shutdown(socket.SHUT_RDWR)
                else:
                    epoll.modify(fileno, select.EPOLLIN)

            elif event & select.EPOLLHUP: # if a POLLHUP event is detected.
                epoll.unregister(fileno)
                connections[fileno].close() # We abort the connection.
                del connections[fileno]
finally:
    epoll.unregister(serversocket.fileno())
    epoll.close()
    serversocket.close()
