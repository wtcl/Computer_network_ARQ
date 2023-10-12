import socket

def client_program():
	n = 4
	win_start = 0
	win_end = win_start + n - 1
	host = '127.0.0.1'  # as both code is running on same pc
	port = 12344  # socket server port number
	sender = []
	flag = 0 #send whole sender list else 1 means send only win_start frame
	client_socket = socket.socket()  # instantiate
	client_socket.connect((host, port))  # connect to the server
	print('Window Size is ', n)
	print('******** Enter "bye" to close connection ***************')
	message = input("Hit any key to start sending frames -> ")  # take input
	while message.lower().strip() != 'bye':
		print("Sending frames...")
		if (flag == 0):
			for i in range(n):
				sender.append(win_start + i)
			for i in sender :
				print("Frame -> ", i)
		else:
			print("Frame -> ", win_start)
		msg = str(win_start)
		client_socket.send(msg.encode())  # send message
		data = client_socket.recv(1024).decode()  # receive NAK
		msg = str(data)
		ack = int(msg)
		if ack not in sender:
			win_start = ack
			win_end = win_start + n - 1
			flag = 0         		#send new frame
			for i in range(n):
				sender.pop()
		else:
			win_start = int(msg)
			flag = 1			#send old frame
			
		print("************************************")
		print('Received ACK server: ' + data)  # show in terminal
		
		message = input("Hit any key to start sending frames -> ")  # again take input

		client_socket.close()  # close the connection


if __name__ == '__main__':
	client_program()

