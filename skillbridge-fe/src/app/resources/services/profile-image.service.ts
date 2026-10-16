import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ProfileImageService {
  private readonly profileImageSubject = new BehaviorSubject<string | null>(this.getStoredProfileImage());
  readonly profileImage$ = this.profileImageSubject.asObservable();

  updateProfileImage(profileImage: string | null | undefined): void {
    /*
     * Subscribers render this straight into an <img> src, so normalise the
     * "no image" cases to a single null rather than pushing undefined.
     */
    this.profileImageSubject.next(profileImage ?? null);
  }

  private getStoredProfileImage(): string | null {
    try {
      const userData = JSON.parse(localStorage.getItem('userData') || '{}');
      return userData.profile_picture_url || userData.profile_image || null;
    } catch {
      return null;
    }
  }
}
