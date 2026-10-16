import { Component, OnInit } from '@angular/core';
import { SocketService } from './resources/services/socket.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  title = 'skillbridge-admin';
//   constructor(
//     private socketService: SocketService,
//   ) {

//   }
//   ngOnInit(): void {
//   const userId = JSON.parse(localStorage.getItem('user_id') || 'null');

//   if (userId) {
//     this.socketService.connect(userId);
//   }
// }
}
