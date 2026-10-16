import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { LoadingServiceService } from '../../resources/services/loading-service.service';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';
import { HttpClient } from '@angular/common/http';
import { ChatboxComponent } from '../../resources/Modals/chatbox/chatbox.component';
import { Dialog, DialogRef } from '@angular/cdk/dialog';
import { ChatMessage, ChatRoom } from '../../resources/models';
import { ChatService } from '../../resources/services/socket.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-chat-list',
  templateUrl: './chat-list.component.html',
  styleUrls: ['./chat-list.component.scss']
})
export class ChatListComponent implements OnInit, OnDestroy {
  loggedInUser: any;
  chatlist: any;
  rooms: ChatRoom[] = [];
  filteredRooms: ChatRoom[] = [];
  LoggedinUserId = this.readStoredUserId();
  loading = true;
  error: string | null = null;

  searchTerm:any;
  skeletons = Array.from({ length: 5 });
  private messageSubscription?: Subscription;

  private readStoredUserId(): string {
    const storedUserId = localStorage.getItem('user_id');
    if (!storedUserId) {
      return '';
    }

    try {
      return JSON.parse(storedUserId) || '';
    } catch {
      return storedUserId;
    }
  }

  /** Soft gradient palette for avatar fallbacks (keyed off the name hash). */
  private palettes = [
    'linear-gradient(135deg, #6366f1, #4f46e5)',
    'linear-gradient(135deg, #0ea5e9, #2563eb)',
    'linear-gradient(135deg, #10b981, #059669)',
    'linear-gradient(135deg, #f59e0b, #ea580c)',
    'linear-gradient(135deg, #ec4899, #db2777)',
    'linear-gradient(135deg, #14b8a6, #0d9488)',
  ];
  constructor(private route:Router,
    private loadingservice:LoadingServiceService,
    private http:HttpClient,
    private dialog: Dialog,
    private chatService: ChatService
  ){
    this.loggedInUser=JSON.parse(localStorage.getItem('userData')|| '{}')
  }

  ngOnInit(): void {
    this.getchatlist();
    this.messageSubscription = this.chatService.newMessage$.subscribe(message => this.updateChatList(message));
  }

  ngOnDestroy(): void {
    this.messageSubscription?.unsubscribe();
  }

   getchatlist(){
   
      this.loadingservice.setLoading()
      let params:URLSearchParams=new URLSearchParams()
      params.set('user_id', this.readStoredUserId())
      this.http.get(environment.apiUrl+ apiLists.chat_room_list+'?'+params).subscribe({
        next:(res:any)=>{
          this.chatlist = res.filter((x: any) => x.last_message);
          this.filteredRooms = this.chatlist;
          this.loadingservice.setSuccess()
          this.loading=false
        },
        error:(err:any)=>{
          console.log(err)
          this.loadingservice.setError()
        }
      })
    }

  private updateChatList(message: ChatMessage): void {
    if (!Array.isArray(this.chatlist)) return;

    const roomIndex = this.chatlist.findIndex((room: ChatRoom) => room.chat_room_id === message.chat_room_id);
    if (roomIndex < 0) {
      this.getchatlist();
      return;
    }

    const room = {
      ...this.chatlist[roomIndex],
      last_message: message
    };
    this.chatlist = [room, ...this.chatlist.filter((_: unknown, index: number) => index !== roomIndex)];
    this.filteredRooms = this.chatlist;
  }

  logout(){
  localStorage.clear()
  this.route.navigateByUrl('auth/login')
}

 getDisplayName(room: ChatRoom): string {
    if (room.name) return room.name;
    const other = room.members?.find((m) => m.user_id !== this.LoggedinUserId);
    return other?.full_name ?? room.members?.[0]?.full_name ?? 'Unknown';
  }

getInitials(name: string): string {
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return '?';
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  }

  getPreview(room: ChatRoom): string {
    const msg = room.last_message?.content?.trim();
    if (!msg) return 'No messages yet';
    return msg.replace(/\s+/g, ' ');
  }

  isOwnMessage(room: ChatRoom): boolean {
    return room.last_message?.sender_id === JSON.parse(localStorage.getItem('user_id') ?? '');
  }

  /** Treat the last message as "unread" when it was sent by the other party. */
  isUnread(room: ChatRoom): boolean {
    return !!room.last_message && room.last_message.sender_id !== JSON.parse(localStorage.getItem('user_id') ?? '');
  }

  /** Deterministic gradient based on the display name. */
  avatarColor(name: string): string {
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return this.palettes[Math.abs(hash) % this.palettes.length];
  }

  /** Relative-ish formatting: time today, "Yesterday", weekday, or date. */
  formatTime(iso: string): string {
    if (!iso) return '';
    const date = new Date(iso);
    if (isNaN(date.getTime())) return '';

    const now = new Date();
    const sameDay = date.toDateString() === now.toDateString();

    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    const isYesterday = date.toDateString() === yesterday.toDateString();

    if (sameDay) {
      return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
    }
    if (isYesterday) return 'Yesterday';

    const diffDays = (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24);
    if (diffDays < 7) {
      return date.toLocaleDateString(undefined, { weekday: 'short' });
    }
    return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  }


  trackByRoom(_index: number, room: ChatRoom): string {
    return room.chat_room_id;
  }

  clearSearch(): void {
    this.searchTerm = '';
    // this.applyFilter();
  }

  onSearch(term: any): void {
    this.searchTerm = term;
    // this.applyFilter();
  }

   openChatfromList(data: any): void {
    const isMobile = window.innerWidth < 768;
     const payload = {
    user_id: JSON.parse(localStorage.getItem('user_id') || ''),
    target_user_id: data.members.user_id
  };
  const tutorDATA = {
    user: {
      id: data.members[0]['user_id'],
      full_name: data.members[0]['full_name'],
      email: data.members[0]['email']
    }
  }
  
        const dialogRef = this.dialog.open(ChatboxComponent, {
    height: '100%',
     width: isMobile ? '100%' : '450px',
    panelClass: 'profile-drawer',
    
    data: {
      tutor: tutorDATA,
      chat_id: data.chat_room_id,
      user_id: JSON.parse(localStorage.getItem('user_id') || '')
    }
  });
 
  }

}
