import { Dialog } from '@angular/cdk/dialog';
import { ReportDialogComponent } from '../../resources/Modals/report-dialog/report-dialog.component';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';
import { MyDetailsCardComponent } from '../../resources/Modals/my-details-card/my-details-card.component';
import { ServiceCardComponent } from '../../resources/Modals/service-card/service-card.component';
import { LoadingServiceService } from '../../resources/services/loading-service.service';
import { ActivatedRoute } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { BookServiceComponent } from '../../resources/Modals/book-service/book-service.component';
import { ChatboxComponent } from '../../resources/Modals/chatbox/chatbox.component';
import { ReviewsComponent } from '../../resources/Modals/reviews/reviews.component';
import { ChatRoomService } from '../../resources/services/chat-room.service';

@Component({
  selector: 'app-view-tutor',
  templateUrl: './view-tutor.component.html',
  styleUrls: ['./view-tutor.component.scss']
})
export class ViewTutorComponent implements OnInit {
  myDetails: any
  overAllDetails: any
  tutor_id:any;
  profile_img: any;
  cover_img: string | null = null;
  selectedFile: File | null = null;
  selectedImagePreview: string | null = null;
  services:any[]=[]
  activeMediaByService: Record<string, string> = {};
  student_ID: any = localStorage.getItem('student_id')
  readonly isStudent = (localStorage.getItem('user_ROLE') || '').replace(/"/g, '').toUpperCase() === 'STUDENT';
  today = new Date()
  constructor(
    private dialog: Dialog,
    private http: HttpClient,
    private loadingService: LoadingServiceService,
    private routed: ActivatedRoute,
    private toastr: ToastrService,
    private chatRooms: ChatRoomService
  ) { }

  ngOnInit(): void {
    this.routed.paramMap.subscribe((x:any)=>{
    this.getUserDetails(x.params.id);
    this.getServices(x.params.id)
     this.tutor_id = x.params.id 
    })
  }

  getUserDetails(id:String | any): void {
    this.loadingService.setLoading();
    console.log(this.myDetails);

    let params: URLSearchParams = new URLSearchParams();
    params.set('tutor_id', id);
    this.http.get<any>(environment.apiUrl + apiLists.tutor_profile_get + '?' + params.toString()).subscribe({
      next: (response) => {
        console.log('==', response);
        this.myDetails = response?.data[0]
        this.loadingService.setSuccess()
        this.profile_img = response?.data[0]['profile_picture_url']
        this.cover_img = response?.data[0]['cover_picture_url'] || response?.data[0]['cover_img'] || null;
        // this.toastr.success('Tutor details fetched successfully')
      },
      error: () => {
        this.loadingService.setError()
        // this.toastr.error('Error fetching tutor details', 'Error');
      }
    });
  }

  getServices(id:String | any): void {
    let params:URLSearchParams=new URLSearchParams
    params.set('tutor_id', id)
  this.http
    .get<any[]>(`${environment.apiUrl}service/services/`+'?'+params)
    .subscribe({
      next: (response:any) => {
        
        this.services = response.data || [];
        this.services.forEach((service: any) => {
          const media = this.getServiceMedia(service);
          this.activeMediaByService[service.id] = media[0] || '';
        });

      },

      error: (error) => {
        console.error('Error fetching services', error);
      }
    });
}

  getServiceMedia(service: any): string[] {
    const images = Array.isArray(service?.image_urls) ? service.image_urls.filter(Boolean) : [];
    const videos = Array.isArray(service?.video_urls) ? service.video_urls.filter(Boolean) : [];
    const singleVideo = service?.video_url ? [service.video_url] : [];
    return [...images, ...videos, ...singleVideo];
  }

  getServiceThumbnail(service: any): string | null {
    const media = this.getServiceMedia(service);
    return media[0] || null;
  }

  setActiveMedia(serviceId: string, mediaUrl: string): void {
    this.activeMediaByService[serviceId] = mediaUrl;
  }

  isVideoUrl(url: string): boolean {
    return /\.(mp4|webm|ogg)$/i.test(url);
  }

   bookService(item:any){
      let dialog = this.dialog.open(BookServiceComponent, {
        height: '100%',
        panelClass: 'profile-drawer',
        data: item,
      })
  
      dialog.closed.subscribe((result: any) => {
        if(result){
          this.ngOnInit()
        }
      });
    }

 openChat(tutor: any): void {
    const isMobile = window.innerWidth < 768;

    this.chatRooms.createDirectRoom(tutor?.user?.id).subscribe({
      next: (res) => {
        this.dialog.open(ChatboxComponent, {
          height: '100%',
          width: isMobile ? '100%' : '450px',
          panelClass: 'profile-drawer',

          data: {
            tutor: tutor,
            chat_id: res.chat_room_id,
            user_id: JSON.parse(localStorage.getItem('user_id') || 'null')
          }
        });
      },
      error: (error) => this.toastr.error(this.chatRooms.failureMessage(error))
    });
  }

  openReviewModal(){
    console.log(this.tutor_id)
    const dialog = this.dialog.open(ReviewsComponent,{
      height:'100%',
       panelClass: 'profile-drawer',
       data:{
        type:'tutor',
        student_id:this.student_ID,
        tutor_id:this.tutor_id,
        service:null
       }
    })
  }

  reportTutor(): void {
    this.submitReport(
      apiLists.report_tutor,
      { tutor_id: this.tutor_id },
      'Tutor',
      this.myDetails?.user?.full_name
    );
  }

  reportService(serviceId: string): void {
    const service = this.services.find((item: any) => item?.id === serviceId);
    this.submitReport(
      apiLists.report_service,
      { service_id: serviceId },
      'Service',
      service?.service_name
    );
  }

  private submitReport(
    endpoint: string,
    target: Record<string, string>,
    label: string,
    entityName?: string | null
  ): void {
    // The dialog owns validation and the POST, so a refused reason stays on
    // screen instead of being lost with the prompt.
    this.dialog.open(ReportDialogComponent, {
      panelClass: ['profile-drawer'],
      data: { endpoint, target, label, entityName }
    });
  }

    pastDateCheck(date:String | any){
  return new Date(date) > this.today
}

}
