/* Minimal localhost WebSocket transport for Chrome DevTools, using only Node built-ins. */
const net = require('node:net');
const crypto = require('node:crypto');
module.exports = class CDPSocket {
  constructor(address) {
    const url = new URL(address);
    this.readyState = 0;
    this.buffer = Buffer.alloc(0);
    this.fragments = [];
    this.socket = net.createConnection({host:url.hostname,port:Number(url.port)});
    this.socket.setNoDelay(true);
    this.socket.on('connect', () => this.socket.write(`GET ${url.pathname} HTTP/1.1\r\nHost: ${url.host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${crypto.randomBytes(16).toString('base64')}\r\nSec-WebSocket-Version: 13\r\n\r\n`));
    this.socket.on('error', error => this.onerror?.({message:error.message,error}));
    this.socket.on('close', () => {this.readyState=3;});
    this.socket.on('data', chunk => {
      this.buffer=Buffer.concat([this.buffer,chunk]);
      if (this.readyState===0) {
        const end=this.buffer.indexOf('\r\n\r\n');
        if(end<0) return;
        const headers=this.buffer.subarray(0,end).toString();
        if(!headers.startsWith('HTTP/1.1 101')) {this.onerror?.({message:headers.split('\r\n')[0]});this.socket.end();return;}
        this.buffer=this.buffer.subarray(end+4);this.readyState=1;this.onopen?.();
      }
      while(this.buffer.length>=2) {
        const first=this.buffer[0],second=this.buffer[1],opcode=first&15;
        let length=second&127,offset=2;
        if(length===126){if(this.buffer.length<4)return;length=this.buffer.readUInt16BE(2);offset=4;}
        else if(length===127){if(this.buffer.length<10)return;length=Number(this.buffer.readBigUInt64BE(2));offset=10;}
        const masked=second&128;if(masked)offset+=4;
        if(this.buffer.length<offset+length)return;
        let body=this.buffer.subarray(offset,offset+length);
        if(masked){const mask=this.buffer.subarray(offset-4,offset);body=Buffer.from(body);for(let i=0;i<body.length;i++)body[i]^=mask[i%4];}
        this.buffer=this.buffer.subarray(offset+length);
        if(opcode===8){this.socket.end();return;}
        if(opcode===9){this.writeFrame(body,10);continue;}
        if(opcode===1||opcode===0){this.fragments.push(body);if(first&128){const data=Buffer.concat(this.fragments).toString();this.fragments=[];this.onmessage?.({data});}}
      }
    });
  }
  writeFrame(body,opcode=1) {
    const mask=crypto.randomBytes(4),size=body.length;
    const prefix=size<126?2:size<=65535?4:10;
    const frame=Buffer.alloc(prefix+4+size);frame[0]=128|opcode;
    frame[1]=128|(size<126?size:size<=65535?126:127);
    if(prefix===4)frame.writeUInt16BE(size,2);else if(prefix===10)frame.writeBigUInt64BE(BigInt(size),2);
    mask.copy(frame,prefix);for(let i=0;i<size;i++)frame[prefix+4+i]=body[i]^mask[i%4];
    this.socket.write(frame);
  }
  send(text) {this.writeFrame(Buffer.from(text));}
  close() {if(this.readyState===1)this.writeFrame(Buffer.alloc(0),8);this.socket.end();}
};
