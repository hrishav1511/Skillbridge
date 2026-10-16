import { Dialog, DialogModule } from '@angular/cdk/dialog';
import { Component, OnInit } from '@angular/core';
import { MyDetailsCardComponent } from '../../resources/Modals/my-details-card/my-details-card.component';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';
import { LoadingServiceService } from '../../resources/services/loading-service.service';
import { ImageCroppedEvent } from 'ngx-image-cropper';
import { ProfileImageService } from '../../resources/services/profile-image.service';
import { ToastrService } from 'ngx-toastr';
@Component({
  selector: 'app-my-profile',
  templateUrl: './my-profile.component.html',
  styleUrls: ['./my-profile.component.scss']
})
export class MyProfileComponent implements OnInit {
readonly COVER_ASPECT_RATIO = 3 / 1;

  myDetails: any
  overAllDetails: any
  profileError: string | null = null;
  tutor_id: string = '';
  profile_img: any;
  selectedFile: File | null = null;
  selectedImagePreview: string | null = null;
  cover_img: string | null = null;
  showCoverCropper = false;
  coverImageChangedEvent: Event | null = null;
  croppedCoverPreview: string | null = null;
  private croppedCoverBlob: Blob | null = null;
  hasCropped = false;
  constructor(private dialog: Dialog,
     private http: HttpClient, 
     private loadingService: LoadingServiceService,
      private profileImageService: ProfileImageService,
    private toastr:ToastrService) { }

  ngOnInit(): void {
    this.getUserDetails();
  }

  getUserDetails(): void {
    this.tutor_id = localStorage.getItem('tutor_id') || '';

    if (!this.tutor_id) {
      this.applyMissingProfile('We could not identify your tutor profile. Please sign in again.');
      return;
    }

    this.loadingService.setLoading();

    let params: URLSearchParams = new URLSearchParams();
    params.set('tutor_id', this.tutor_id);
    this.http.get<any>(environment.apiUrl + apiLists.tutor_profile_get + '?' + params.toString()).subscribe({
      next: (response) => {
        /*
         * The list endpoint answers with an array. An empty array is a valid
         * answer, so read it as "no profile" rather than indexing into it and
         * dereferencing undefined.
         */
        const profile = response?.data?.[0];

        if (!profile) {
          this.applyMissingProfile('We could not load your tutor profile.');
          return;
        }

        this.profileError = null;
        this.myDetails = profile;
        this.profile_img = profile.profile_picture_url ?? null;
        this.cover_img = profile.cover_picture_url ?? null;
        this.profileImageService.updateProfileImage(this.profile_img);
        this.loadingService.setSuccess();
      },
      error: () => {
        this.applyMissingProfile('We could not load your tutor profile.');
      }
    });
  }

  /** Leave the view in a consistent "no profile" state instead of a half-filled one. */
  private applyMissingProfile(message: string): void {
    this.profileError = message;
    this.myDetails = null;
    this.profile_img = null;
    this.cover_img = null;
    this.profileImageService.updateProfileImage(null);
    this.loadingService.setError();
  }

  get initials(): string {
    const name = this.myDetails?.user?.full_name?.trim() || '';
    if (!name) return 'NV';
    const parts = name.split(/\s+/);
    return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase();
  }

  toggleVisibility(): void {
    const newValue = !this.myDetails?.is_visible;
    this.loadingService.setLoading();
    const url = environment.apiUrl + apiLists.tutor_visibility;
    this.http.patch(url, { is_visible: newValue }).subscribe({
      next: (res:any) => {
        this.getUserDetails()
        this.loadingService.setSuccess();
        this.toastr.success(res?.is_visible ? 'Profile is now visible' : 'Profile is now hidden');
      },
      error: () => {
        this.loadingService.setError();
      }
    });
  }

  editdetails() {
    // this.myDetails?.tutor_id = this.tutor_id;
    const flattenedData = {
      ...this.myDetails,
      full_name: this.myDetails?.user?.full_name,
      email: this.myDetails?.user?.email,
      user_phone: this.myDetails?.user?.phone,
      tutor_id: this.tutor_id
    };
    const dialogref = this.dialog.open(MyDetailsCardComponent, {
      height: '100%',
      panelClass: 'profile-drawer',
      data: flattenedData,
    });


    dialogref.closed.subscribe((result: any) => {
      // Profile edits are staged for admin approval, so the values on screen
      // will not change yet. Say so, otherwise a saved edit reads as lost.
      if (result?.pendingApproval) {
        this.toastr.info(result.message, 'Awaiting approval');
      }
      this.getUserDetails()
    })
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;

    if (!input.files?.length) {
      return;
    }

    this.selectedFile = input.files[0];

    const reader = new FileReader();

    reader.onload = () => {
      this.selectedImagePreview = reader.result as string;
    };

    reader.readAsDataURL(this.selectedFile);
  }

  saveProfileImage(): void {
    if (!this.selectedFile) {
      return;
    }

    const formData = new FormData();
    const uploadurl = environment.apiUrl + apiLists.profile_pic_update + this.tutor_id + '/upload-profile-picture/';
    formData.append('file', this.selectedFile);
    this.http.post(uploadurl, formData).subscribe({
      next: (response: any) => {
        this.getUserDetails()
        this.profileImageService.updateProfileImage(this.selectedImagePreview)
        this.loadingService.setSuccess()
        this.selectedFile = null;
      },
      error: (error) => {
        // this.loading = false;
        this.loadingService.setError()
        console.error('Tutor profile error:', error);
        // this.error = error?.error?.message || 'Tutor profile creation failed. Please try again.';
      }
    });
   
  }
  //Cover picture workflow

  onCoverSelected(event: Event): void {
  const input = event.target as HTMLInputElement;
  if (!input.files?.length) return;
  this.coverImageChangedEvent = event;
  this.croppedCoverPreview = null;
  this.showCoverCropper = true;
  console.log('Cover selected:', input.files);

}
onCoverCropped(event: ImageCroppedEvent| any): void {
  console.log('CROPPED EVENT:', event);
  this.croppedCoverPreview = event.base64 ?? null;
  this.croppedCoverBlob = event.blob ?? null;
  this.hasCropped = true
}

get canSaveCover(): boolean {
  return !!this.croppedCoverBlob || !!this.croppedCoverPreview;
}
cancelCoverCrop(): void {
  this.showCoverCropper = false;
  this.coverImageChangedEvent = null;
  this.croppedCoverPreview = null;
  this.croppedCoverBlob = null;
}

saveCover(): void {
  if (!this.croppedCoverBlob) return;

  // Optimistic local preview
  this.cover_img = this.croppedCoverPreview;
  this.loadingService.setLoading()
  const form = new FormData();
  form.append('file', this.croppedCoverBlob, 'cover.png');
  // this.profileService.uploadCover(form).subscribe(res => this.cover_img = res.url);
  this.http.post(environment.apiUrl + apiLists.coverpic_update + this.tutor_id + '/upload-cover-picture/', form).subscribe({
    next: (response: any) => {
      this.loadingService.setSuccess()
      this.getUserDetails()
    }
  })
  this.showCoverCropper = false;
  this.coverImageChangedEvent = null;
  this.croppedCoverBlob = null;
}
}
