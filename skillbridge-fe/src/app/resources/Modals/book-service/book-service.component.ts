import { DialogRef, DIALOG_DATA } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, Inject } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { LoadingServiceService } from '../../services/loading-service.service';
import { apiLists } from '../../apiLists';
import { environment } from '../../../../environments/environment';
import { ToastrService } from 'ngx-toastr';
import { Router } from '@angular/router';
import { MediaItem } from '../../models';

@Component({
  selector: 'app-book-service',
  templateUrl: './book-service.component.html',
  styleUrls: ['./book-service.component.scss']
})
export class BookServiceComponent {

  service: any;
  isClosing = false;
  mediaItems: MediaItem[] = [];
  selectedMediaItem: MediaItem | null = null;
  showMediaFallback = false;

  constructor(
    private fb: FormBuilder,
    private dialogRef: DialogRef<BookServiceComponent>,
    @Inject(DIALOG_DATA) public data: any,
    private http: HttpClient,
    private loadingService: LoadingServiceService,
    private toastr: ToastrService,
    private router: Router
  ) {
    this.service = data;
    this.buildMediaItems();
  }

  private buildMediaItems(): void {
    if (!this.service) {
      this.mediaItems = [];
      this.selectedMediaItem = null;
      return;
    }

    const imageUrls = Array.isArray(this.service.image_urls)
      ? this.service.image_urls.filter((url: string | null | undefined) => !!url)
      : [];

    const videoUrls = Array.isArray(this.service.video_urls)
      ? this.service.video_urls.filter((url: string | null | undefined) => !!url)
      : [];

    const singleVideoUrl = this.service.video_url ? [this.service.video_url] : [];
    const allVideoUrls = [...videoUrls, ...singleVideoUrl.filter((url: string) => !videoUrls.includes(url))];

    this.mediaItems = [
      ...imageUrls.map((url: string) => ({ type: 'image' as const, url })),
      ...allVideoUrls.map((url: string) => ({ type: 'video' as const, url }))
    ];

    this.selectedMediaItem = this.mediaItems[0] || null;
    this.showMediaFallback = false;
  }

  selectMedia(item: MediaItem): void {
    this.selectedMediaItem = item;
    this.showMediaFallback = false;
  }

  handleMediaError(event: Event): void {
    const target = event.target as HTMLImageElement | null;
    if (!target) {
      return;
    }

    target.style.display = 'none';
    this.showMediaFallback = true;
  }

  close(): void {
    this.isClosing = true;

    setTimeout(() => {
      this.dialogRef.close();
    }, 300);
  }

  confirmBooking(): void {
    // const studentId = localStorage.getItem('student_id');
    // let payload ={
    //   student_id: studentId,
    //   service_id: this.service.id
    // }

    // this.http.post<any>(`${environment.apiUrl}${apiLists.service_booking}`, payload).subscribe({
    //     next: (response) => {
    //     console.log('Service booked successfully:', response);
    //     this.toastr.success('Service booked successfully');
    //     this.close();
    //   },
    //   error: (error) => {
    //     console.error('Error booking service:', error);
    //     this.toastr.error(error.error.detail || 'Failed to book service', 'Error');
    //   }
    // })
    this.loadingService.setLoading();

    setTimeout(() => {
      this.loadingService.reset();
      this.dialogRef.close();
        this.router.navigate(['/student/payment', this.service.id], {
          state: { service: this.service }
        });
    }, 1000);
  }
}

