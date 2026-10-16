import { TestBed } from '@angular/core/testing';

import { ChatService } from './socket.service';

describe('ChatService', () => {
  let service: ChatService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ChatService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('does not attempt a WebSocket connection without an access token', () => {
    localStorage.removeItem('access_token');
    const webSocketSpy = spyOn(window, 'WebSocket');

    expect(service.connect('user-id')).toBeFalse();
    expect(webSocketSpy).not.toHaveBeenCalled();
  });

  it('publishes messages sent by the current user so the open chat updates', () => {
    localStorage.setItem('access_token', 'token');
    localStorage.setItem('user_id', JSON.stringify('user-id'));
    const socket: any = {
      readyState: WebSocket.CONNECTING,
      send: jasmine.createSpy('send'),
      close: jasmine.createSpy('close')
    };
    spyOn(window, 'WebSocket').and.returnValue(socket);
    let received: any;
    service.newMessage$.subscribe(message => { received = message; });

    service.connect('user-id');
    socket.onmessage({
      data: JSON.stringify({
        event: 'new_message',
        payload: { chat_room_id: 'room-id', sender_id: 'user-id', content: 'sent' }
      })
    });

    expect(received.content).toBe('sent');
    service.disconnect();
  });

  it('queues a message while connecting and flushes it when connected', () => {
    localStorage.setItem('access_token', 'token');
    const socket: any = {
      readyState: WebSocket.CONNECTING,
      send: jasmine.createSpy('send'),
      close: jasmine.createSpy('close')
    };
    spyOn(window, 'WebSocket').and.returnValue(socket);

    service.connect('user-id');
    expect(service.sendMessage('room-id', 'hello')).toBeTrue();
    expect(socket.send).not.toHaveBeenCalled();
    socket.readyState = WebSocket.OPEN;
    socket.onopen();

    expect(socket.send).toHaveBeenCalledTimes(1);
    expect(socket.send.calls.mostRecent().args[0]).toContain('hello');
    service.disconnect();
  });
});
