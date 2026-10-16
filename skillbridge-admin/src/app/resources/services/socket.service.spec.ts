import { TestBed } from '@angular/core/testing';

import { SocketService } from './socket.service';

describe('SocketService', () => {
  let service: SocketService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SocketService);
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('queues an admin message until the authenticated socket opens', () => {
    localStorage.setItem('access_token', 'token');
    const socket: any = {
      readyState: WebSocket.CONNECTING,
      send: jasmine.createSpy('send'),
      close: jasmine.createSpy('close')
    };
    spyOn(window, 'WebSocket').and.returnValue(socket);

    service.connect('admin-id');
    expect(service.sendMessage('room-id', 'hello tutor')).toBeTrue();
    expect(socket.send).not.toHaveBeenCalled();
    socket.readyState = WebSocket.OPEN;
    socket.onopen();

    expect(socket.send).toHaveBeenCalledTimes(1);
    expect(socket.send.calls.mostRecent().args[0]).toContain('hello tutor');
    service.disconnect();
  });
});
