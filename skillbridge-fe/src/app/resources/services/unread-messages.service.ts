import { HttpClient } from '@angular/common/http';
import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Subscription } from 'rxjs';
import { environment } from '../../../environments/environment';
import { apiLists } from '../apiLists';
import { ChatService } from './socket.service';

interface ChatRoomSummary {
  chat_room_id: string;
  unread_count?: number;
}

/**
 * How many *conversations* have unread messages.
 *
 * Deliberately a count of rooms rather than of messages: the navbar badge
 * answers "how many people are waiting on me", so five messages in one thread
 * is still one.
 *
 * Both navbars read the same instance, so the badge cannot disagree with
 * itself between the student and tutor shells.
 */
@Injectable({ providedIn: 'root' })
export class UnreadMessagesService implements OnDestroy {
  private readonly roomsWithUnread = new Set<string>();
  private readonly countSubject = new BehaviorSubject<number>(0);
  readonly unreadConversations$ = this.countSubject.asObservable();

  private socketSubscription?: Subscription;
  private started = false;

  constructor(private http: HttpClient, private chatService: ChatService) {}

  /** Safe to call more than once; only the first call does anything. */
  start(): void {
    if (this.started) {
      return;
    }
    this.started = true;

    this.refresh();

    this.socketSubscription = this.chatService.newMessage$.subscribe(message => {
      if (!message?.chat_room_id) {
        return;
      }
      // A message I sent is not unread for me.
      const currentUserId = this.readUserId();
      if (currentUserId && String(message.sender_id) === currentUserId) {
        return;
      }
      this.markUnread(String(message.chat_room_id));
    });
  }

  ngOnDestroy(): void {
    this.socketSubscription?.unsubscribe();
  }

  /** Re-read the authoritative counts from the room list. */
  refresh(): void {
    this.http.get<ChatRoomSummary[]>(environment.apiUrl + apiLists.chat_room_list)
      .subscribe({
        next: rooms => {
          this.roomsWithUnread.clear();
          (rooms || []).forEach(room => {
            if ((room.unread_count || 0) > 0) {
              this.roomsWithUnread.add(String(room.chat_room_id));
            }
          });
          this.publish();
        },
        // A failed refresh must not wipe a badge that was previously correct.
        error: () => undefined
      });
  }

  markUnread(chatRoomId: string): void {
    if (!this.roomsWithUnread.has(chatRoomId)) {
      this.roomsWithUnread.add(chatRoomId);
      this.publish();
    }
  }

  /** Called when a conversation is opened; the thread is now read. */
  markRoomRead(chatRoomId: string | null | undefined): void {
    if (chatRoomId && this.roomsWithUnread.delete(String(chatRoomId))) {
      this.publish();
    }
  }

  private publish(): void {
    this.countSubject.next(this.roomsWithUnread.size);
  }

  private readUserId(): string | null {
    try {
      const raw = localStorage.getItem('user_id');
      return raw ? String(JSON.parse(raw)) : null;
    } catch {
      return null;
    }
  }
}
