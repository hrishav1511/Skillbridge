import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { apiLists } from '../apiLists';

export interface DirectRoom {
  chat_room_id: string;
  room_type: string;
}

/**
 * Opening a direct chat was duplicated across four components, each building
 * the request by hand. Two of them disagreed about whether target_user_id is a
 * query parameter or a body field, and one passed a tutor id where a user id
 * belongs, so the request 422'd and - with no error handler anywhere - the
 * click did nothing at all.
 */
@Injectable({ providedIn: 'root' })
export class ChatRoomService {
  constructor(private http: HttpClient) {}

  /**
   * @param targetUserId the *user* id of the person to talk to, never a tutor id.
   */
  createDirectRoom(targetUserId: string | null | undefined): Observable<DirectRoom> {
    if (!targetUserId) {
      /*
       * Sending an empty id produced an opaque 422. Failing here keeps the
       * reason readable and lets the caller show it.
       */
      return throwError(() => new Error('This tutor cannot be messaged right now.'));
    }

    const params = new URLSearchParams();
    params.set('target_user_id', targetUserId);
    return this.http.post<DirectRoom>(
      `${environment.apiUrl}${apiLists.chat_room_creation}?${params}`,
      {}
    );
  }

  /** Message shown to the user when a chat cannot be opened. */
  failureMessage(error: any): string {
    if (error instanceof Error) {
      return error.message;
    }
    return error?.error?.detail || 'We could not open this conversation. Please try again.';
  }
}
