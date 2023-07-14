
# P2P Chat

This application is a peer-to-peer chat platform that allows users to communicate securely over local networks. It utilizes Multicast DNS (mDNS) for local service discovery and the Noise Protocol Framework for establishing secure communication channels.


## Features

- peer-to-peer connection
- local peer discovery (using mDNS)
- secure channel for communication
- chat request system


## Requirements

- Py-Qt6
- noiseprotocol
- zeroconf
    
## FAQ

#### It doesn't send request to another peer, how to fix it?
Windows firewall might be blocking the request, here's how to fix it
 - open windows firewall
 - add a new rule under inboud connection
 - select the application 

#### What protocol does it uses for security?

It is using 'Noise_NN_25519_ChaChaPoly_SHA256'

#### Note - Only messages are encryped, files are sent directly. 


## Screenshots

![App Screenshot](https://via.placeholder.com/150x200?text=App+Screenshot+Here)
![App Screenshot](https://via.placeholder.com/150x200?text=App+Screenshot+Here)
![App Screenshot](https://via.placeholder.com/150x200?text=App+Screenshot+Here)

