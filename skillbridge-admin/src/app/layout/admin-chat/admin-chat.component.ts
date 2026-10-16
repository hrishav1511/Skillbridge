import {
  AfterViewChecked,
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  OnInit,
  ViewChild
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';
import { environment } from 'src/environments/environment';
import { apilists } from '../../resources/ApiList';
import { SocketService } from '../../resources/services/socket.service';

interface ChatMember {
  user_id: string;
  full_name: string;
  email: string;
}

interface TutorUser {
  id: string;
  full_name: string;
  email: string;
}

interface ChatMessage {
  id: string;
  chat_room_id: string;
  sender_id: string;
  content: string;
  created_at: string;
}

interface ChatRoom {
  chat_room_id: string;
  members: ChatMember[];
  last_message?: ChatMessage | null;
}

interface TutorContact {
  account_status?: string;
  approval_status?: string;
  user?: TutorUser;
}

@Component({
  selector: 'app-admin-chat',
  templateUrl: './admin-chat.component.html',
  styleUrls: ['./admin-chat.component.scss']
})
export class AdminChatComponent implements OnInit, AfterViewChecked, OnDestroy {
  tutors: TutorContact[] = [];
  rooms: ChatRoom[] = [];
  selectedRoom: ChatRoom | null = null;
  messages: ChatMessage[] = [];
  messageText = '';
  error = '';

  /* Typeahead state for picking a tutor to message. */
  tutorSearch = '';
  tutorPickerOpen = false;
  highlightedIndex = -1;
  readonly currentUserId = this.readCurrentUserId();
  private socketSubscription?: Subscription;

  /*
   * The thread is only scrolled once *ngFor has rendered the new rows, so
   * the request handlers raise a flag and ngAfterViewChecked does the work.
   */
  @ViewChild('messageList') private messageList?: ElementRef<HTMLElement>;
  private scrollToLatestPending = false;

  constructor(
    private http: HttpClient,
    private socket: SocketService,
    private elementRef: ElementRef<HTMLElement>
  ) {}

  /**
   * Tutors whose name or email matches what has been typed.
   *
   * The picker was a plain <select>, which is unusable once there are more
   * than a handful of tutors; this narrows the list as you type.
   */
  get filteredTutors(): TutorContact[] {
    const term = this.tutorSearch.trim().toLowerCase();
    if (!term) {
      return this.tutors;
    }
    return this.tutors.filter(tutor => {
      const name = (tutor.user?.full_name || '').toLowerCase();
      const email = (tutor.user?.email || '').toLowerCase();
      return name.includes(term) || email.includes(term);
    });
  }

  openTutorPicker(): void {
    this.tutorPickerOpen = true;
    this.highlightedIndex = -1;
  }

  onTutorSearch(value: string): void {
    this.tutorSearch = value;
    this.tutorPickerOpen = true;
    this.highlightedIndex = -1;
  }

  selectTutor(tutor: TutorContact): void {
    const targetUserId = tutor.user?.id;
    if (!targetUserId) {
      return;
    }
    this.tutorSearch = '';
    this.tutorPickerOpen = false;
    this.highlightedIndex = -1;
    this.startChat(targetUserId);
  }

  /** Arrow keys move the highlight, Enter picks it, Escape closes the list. */
  onPickerKeydown(event: KeyboardEvent): void {
    const options = this.filteredTutors;
    if (event.key === 'Escape') {
      this.tutorPickerOpen = false;
      this.highlightedIndex = -1;
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.tutorPickerOpen = true;
      this.highlightedIndex = Math.min(this.highlightedIndex + 1, options.length - 1);
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.highlightedIndex = Math.max(this.highlightedIndex - 1, 0);
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      const choice = options[this.highlightedIndex] || (options.length === 1 ? options[0] : null);
      if (choice) {
        this.selectTutor(choice);
      }
    }
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as Node | null;
    if (target && !this.elementRef.nativeElement.contains(target)) {
      this.tutorPickerOpen = false;
    }
  }

  ngOnInit(): void {
    this.loadTutors();
    this.loadRooms();
    this.socketSubscription = this.socket.events$.subscribe(event => {
      if (event?.event !== 'new_message' || !event.payload) return;
      if (event.payload.chat_room_id === this.selectedRoom?.chat_room_id) {
        this.messages = [...this.messages, event.payload];
        this.scrollToLatestPending = true;
      }
      this.loadRooms();
    });
  }

  ngAfterViewChecked(): void {
    if (!this.scrollToLatestPending) {
      return;
    }
    const list = this.messageList?.nativeElement;
    if (!list) {
      return;
    }
    this.scrollToLatestPending = false;
    list.scrollTop = list.scrollHeight;
  }

  ngOnDestroy(): void {
    this.socketSubscription?.unsubscribe();
  }

  loadTutors(): void {
    this.http.get<{ data: TutorContact[] }>(`${environment.apiUrl}admin/tutors/`).subscribe({
      next: response => {
        this.tutors = (response.data || []).filter(tutor =>
          tutor.account_status === 'ACTIVE' &&
          tutor.approval_status === 'ACCEPTED' &&
          !!tutor.user?.id
        );
      },
      error: () => { this.error = 'Unable to load tutors.'; }
    });
  }

  loadRooms(openRoomId?: string): void {
    this.http.get<ChatRoom[]>(environment.apiUrl + apilists.chat_rooms).subscribe({
      next: rooms => {
        this.rooms = rooms || [];
        if (openRoomId) {
          const room = this.rooms.find(item => item.chat_room_id === openRoomId);
          if (room) this.openRoom(room);
        }
      },
      error: () => { this.error = 'Unable to load conversations.'; }
    });
  }

  startChat(targetUserId: string): void {
    const params = new URLSearchParams({ target_user_id: targetUserId });
    this.http.post<{ chat_room_id: string }>(
      `${environment.apiUrl}${apilists.direct_chat_room}?${params}`,
      {}
    ).subscribe({
      next: response => this.loadRooms(response.chat_room_id),
      error: error => { this.error = error?.error?.detail || 'Unable to start conversation.'; }
    });
  }

  openRoom(room: ChatRoom): void {
    this.selectedRoom = room;
    this.error = '';
    this.http.get<{ messages: ChatMessage[] }>(
      `${environment.apiUrl}${apilists.chat_rooms}${room.chat_room_id}/messages/?limit=100`
    ).subscribe({
      next: response => {
        this.messages = [...(response.messages || [])].reverse();
        // Opening a conversation must land on the newest message.
        this.scrollToLatestPending = true;
      },
      error: () => { this.error = 'Unable to load message history.'; }
    });
  }

  sendMessage(): void {
    const content = this.messageText.trim();
    if (!content || !this.selectedRoom) return;
    if (this.socket.sendMessage(this.selectedRoom.chat_room_id, content)) {
      this.messageText = '';
      this.error = '';
    } else {
      this.error = 'Chat is unavailable. Your message was not cleared.';
    }
  }

  roomName(room: ChatRoom | null): string {
    return room?.members?.[0]?.full_name || 'Tutor';
  }

  private readCurrentUserId(): string {
    try {
      return JSON.parse(localStorage.getItem('user_id') || 'null') || '';
    } catch {
      return localStorage.getItem('user_id') || '';
    }
  }
}
