import { Component, OnInit } from '@angular/core';
import { SocketService } from '../resources/services/socket.service';

@Component({
  selector: 'app-layout',
  templateUrl: './layout.component.html',
  styleUrls: ['./layout.component.scss']
})
export class LayoutComponent implements OnInit {
constructor(
    private socketService: SocketService,
  ) {

  }
  ngOnInit(): void {
  const userId = JSON.parse(localStorage.getItem('user_id') || 'null');

  if (userId) {
    this.socketService.connect(userId);
  }
}
  ngOnDestroy(): void {
    this.socketService.disconnect();
  }
}
