import { Component, OnInit } from '@angular/core';
import { LoadingState } from './resources/models';
import { LoadingServiceService } from './resources/services/loading-service.service';
import { ChatService } from './resources/services/socket.service';
import { NotificationService } from './resources/services/notification.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {

  loadingState$ = this.loadingService.loadingState$;

  LoadingState = LoadingState;
  // userId: string | null;

  constructor(
    private loadingService: LoadingServiceService,
    private chatService: ChatService,
    private notificationService: NotificationService,
  ) {
    //  this.userId = JSON.parse(localStorage.getItem('user_id') || '');
    //  console.log(this.userId);

  }
  ngOnInit(): void {
    // const userData = localStorage.getItem('user_id');

    // if (userData) {
    //   const user = JSON.parse(userData);

    //   this.chatService.connect(user);

    //   console.log(' Starting notification listener...');
    //   this.notificationService.listenForNotifications();
    // }

    
  }
}
