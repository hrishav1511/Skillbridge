import { Dialog, DialogRef, DIALOG_DATA } from '@angular/cdk/dialog';
import { ReportDialogComponent } from '../report-dialog/report-dialog.component';
import { HttpClient } from '@angular/common/http';
import { Component, Inject, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { LoadingServiceService } from '../../services/loading-service.service';
import { MyDetailsCardComponent } from '../my-details-card/my-details-card.component';
import { environment } from '../../../../environments/environment';
import { apiLists } from '../../apiLists';
import { ToastrService } from 'ngx-toastr';

@Component({
  selector: 'app-reviews',
  templateUrl: './reviews.component.html',
  styleUrls: ['./reviews.component.scss']
})
export class ReviewsComponent  implements OnInit{
  selectedRating = 0;
  reviewForm!:FormGroup
comment = '';
  isClosing:boolean= false
  reviewList: any;
  constructor(
     private fb: FormBuilder,
      private dialogRef: DialogRef<MyDetailsCardComponent>,
      @Inject(DIALOG_DATA) public data: any,
      private http: HttpClient,
      private loadingService: LoadingServiceService,
      private toastr: ToastrService,
      private dialog: Dialog
    ) {}

    ngOnInit(): void {
      this.getData()
      this.reviewForm = this.fb.group({

      comment: [
        '',
        [
          Validators.required,
          Validators.minLength(10),
          Validators.maxLength(500)
        ]
      ]

    });
    }

    getData(){
      const isServiceReview = this.data?.type === 'service';
      const endpoint = isServiceReview ? apiLists.service_review : apiLists.tutor_review;
      const params: URLSearchParams = new URLSearchParams();

      if (isServiceReview) {
        params.set('service_id', this.data?.service?.id ?? this.data?.service_id ?? '');
      } else {
        params.set('tutor_id', this.data?.tutor_id ?? '');
      }

      this.http.get(environment.apiUrl + endpoint + '?' + params).subscribe({
        next:(res:any)=>{
          this.reviewList = res['data']
        }
      })
    }

    setRating(rating: number): void {

  this.selectedRating = rating;

}

submitReview(): void {

   if (this.selectedRating === 0) {
      return;
    }

    if (this.reviewForm.invalid) {

      this.reviewForm.markAllAsTouched();

      return;

    }

  const isServiceReview = this.data?.type === 'service';
  const payload = isServiceReview
    ? {
        service_id: this.data?.service?.id ?? this.data?.service_id,
        student_id: this.data.student_id,
        rating: this.selectedRating,
        comment: this.reviewForm.get('comment')?.value
      }
    : {
        tutor_id: this.data.tutor_id,
        student_id: this.data.student_id,
        rating: this.selectedRating,
        comment: this.reviewForm.get('comment')?.value
      };

  const endpoint = isServiceReview ? apiLists.service_review : apiLists.tutor_review;

  this.http.post(environment.apiUrl + endpoint, payload).subscribe({
    next:(res:any)=>{
      this.getData()
      this.selectedRating =0
      this.reviewForm.reset()
    },
    error:(err:any)=> this.toastr.error(err?.error?.detail || 'Unable to submit review.')
  })

}

canReportReviews(): boolean {
  return !!localStorage.getItem('access_token') && localStorage.getItem('role') !== 'GUEST';
}

reportReview(review: any): void {
  if (!this.canReportReviews() || !review?.id) {
    return;
  }
  const reviewType = this.data?.type === 'service' ? 'service' : 'tutor';
  this.dialog.open(ReportDialogComponent, {
    panelClass: ['profile-drawer'],
    data: {
      endpoint: `${apiLists.report_review}${reviewType}/${review.id}/`,
      target: {},
      label: 'Review',
      entityName: review?.student_name || review?.user?.full_name || null
    }
  });
}

getInitials(name: string): string {

  if (!name) return '?';

  return name
    .split(' ')
    .map(part => part.charAt(0))
    .join('')
    .substring(0, 2)
    .toUpperCase();

}

    close(){
      this.dialogRef.close()
      this.isClosing = true
    }
}
