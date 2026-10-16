import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { Component, ElementRef, Inject, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { ChatService } from '../../services/socket.service';
import { UnreadMessagesService } from '../../services/unread-messages.service';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { apiLists } from '../../apiLists';

@Component({
  selector: 'app-chatbox',
  templateUrl: './chatbox.component.html',
  styleUrls: ['./chatbox.component.scss']
})
export class ChatboxComponent implements OnInit, OnDestroy{

@ViewChild('chatBody')chatBody!: ElementRef;
messages:any = [];

messageText = '';

isTyping = false;

currentUserId = JSON.parse(localStorage.getItem('user_id') || 'null');

typingTimeout: any;
private messageSubscription?: Subscription;
private eventSubscription?: Subscription;

sendMessage(): void {

  if (!this.messageText.trim()) {
    return;
  }
  console.log(this.messageText);
  
  // this.messages.push({
  //   sender: 'me',
  //   content: this.messageText,
  //   time: new Date().toLocaleTimeString()
  // });
  if (this.chatService.sendMessage(this.data.chat_id, this.messageText)) {
    this.messageText = '';
  }
}
  constructor(
  @Inject(DIALOG_DATA)
  public data: any,
  private dialogRef: DialogRef<ChatboxComponent>,
  private chatService:ChatService,
  private http:HttpClient,
  private unreadMessages: UnreadMessagesService
) {}

ngOnInit(): void {
  this.chatService.setActiveChatRoom(this.data.chat_id);
  // Opening the thread reads it, so the navbar badge must drop it.
  this.unreadMessages.markRoomRead(this.data?.chat_id);
  this.messageSubscription = this.chatService.newMessage$.subscribe(message => {
    if (message.chat_room_id === this.data?.chat_id) {
      this.messages.push(message);
      this.scrollToBottom();
      this.unreadMessages.markRoomRead(this.data?.chat_id);
    }
  });
  console.log('data==>', this.data)
  this.eventSubscription = this.chatService.events$.subscribe(event => {
  // console.log(event);
  
  switch(event.event){

    case 'history':
      break;

    case 'new_message':
      break;

    case 'typing':
      console.log(event)
      this.isTyping = event.payload.is_typing      
      break;

    case 'read_receipt':
      break;
  }

});
  this.getChats()

}

ngOnDestroy(): void {
  this.messageSubscription?.unsubscribe();
  this.eventSubscription?.unsubscribe();
  this.chatService.setActiveChatRoom(null);
}

getDetails(){

}
getChats(){
  let params:URLSearchParams= new URLSearchParams
  params.set('user_id', this.data.user_id)
  params.set('limit','30')
  this.http.get(environment.apiUrl + apiLists.chat_specific_msg+this.data.chat_id+'/'+'messages/'+'?'+params).subscribe({
    next:(res:any)=>{
      console.log(res);
      this.messages = [...res.messages].reverse()
      this.scrollToBottom()
    },
    error:(err:any)=>{
      console.log(err)
    }
  })
}
onTyping(){
  this.chatService.setTyping(
        this.data.chat_id,
        true
    );

    clearTimeout(this.typingTimeout);

    this.typingTimeout = setTimeout(() => {

        this.chatService.setTyping(
            this.data.chat_id,
            false
        );

    }, 1200);
}

scrollToBottom(): void {
  setTimeout(() => {
    if (this.chatBody) {
      this.chatBody.nativeElement.scrollTop =
        this.chatBody.nativeElement.scrollHeight;
    }
  }, 50);
}

close(): void {
  this.chatService.setActiveChatRoom(null);
  this.dialogRef.close();
}
}
