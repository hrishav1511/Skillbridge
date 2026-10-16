import { HttpClient } from '@angular/common/http';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { ChatService } from '../../resources/services/socket.service';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';
import { LoadingServiceService } from '../../resources/services/loading-service.service';
import { Dialog } from '@angular/cdk/dialog';
import {
  RescheduleDialogComponent,
  RescheduleDialogResult
} from '../../resources/Modals/reschedule-dialog/reschedule-dialog.component';
import { ChatboxComponent } from '../../resources/Modals/chatbox/chatbox.component';
import {
  ServiceDayDialogComponent,
  ServiceDayDialogResult
} from '../../resources/Modals/service-day-dialog/service-day-dialog.component';
import { NotificationService } from '../../resources/services/notification.service';
import { Router } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { Subscription } from 'rxjs';

/** One square in the month grid. `day` is null for padding cells. */
interface CalendarCell {
  day: number | null;
  date: Date | null;
  isToday: boolean;
  services: any[];
}

@Component({
  selector: 'app-tutor-dashboard',
  templateUrl: './tutor-dashboard.component.html',
  styleUrls: ['./tutor-dashboard.component.scss']
})
export class TutorDashboardComponent implements OnInit, OnDestroy {
  curDate:Date = new Date().setDate(new Date().getDate()) as unknown as Date;
  showProfileMenu = false;
  mobileMenuOpen = false;
  chatlist:any[]=[]
  dashboardData:any;
  loggedInUser: any = {};
  nextServiceCountdown = 'No upcoming services';
  private countdownInterval?: ReturnType<typeof setInterval>;
  private socketSubscription?: Subscription;
  notifcations:any[]=[]
  serviceRequests: any[] = [];
  currentUserId: string | null = JSON.parse(localStorage.getItem('user_id') || 'null');
  tutorId = localStorage.getItem('tutor_id') || '';

  /*
   * Calendar state. The month being viewed is held explicitly rather than read
   * from `new Date()` at build time, which is what makes prev/next possible.
   */
  calendarWeeks: CalendarCell[][] = [];
  calendarServices: any[] = [];
  viewYear = new Date().getFullYear();
  viewMonth = new Date().getMonth();
  readonly weekdayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  constructor(
    private http:HttpClient,
    private chatservice:ChatService,
    private loading:LoadingServiceService,
    private dialog:Dialog,
    private notificationService: NotificationService,
    private router: Router,
    private toastr: ToastrService
  ){

  }

  ngOnInit(): void {
    this.loggedInUser = JSON.parse(localStorage.getItem('userData') || '{}');
    this.updateNextServiceCountdown();
    this.countdownInterval = setInterval(() => this.updateNextServiceCountdown(), 60000);
    this.getDashboardData()
    this.getServiceRequests()
    this.getCalendarServices()
    this.getchatlist()
    this.socketSubscription = this.chatservice.events$
      .subscribe(event => {

        switch (event.event) {

          case 'history':
            break;

          case 'new_message':
            this.updateChatList(event.payload)
            break;

          case 'typing':
            break;

          case 'read_receipt':
            break;
        } 
      })
  }

  ngOnDestroy(): void {
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
    }
    this.socketSubscription?.unsubscribe();
  }
 
  

  getchatlist(){
    // this.loading.setLoading()
    let params:URLSearchParams=new URLSearchParams()
    params.set('user_id',JSON.parse(localStorage.getItem('user_id') || 'null'))
    this.http.get(environment.apiUrl+ apiLists.chat_room_list+'?'+params).subscribe({
      next:(res:any)=>{
        this.chatlist=res.filter((x:any)=> x.last_message !==null)
        // this.loading.setSuccess()
      },
      error:(err:any)=>{
        console.log(err)
        // this.loading.setError()
      }
    })
  }

  getDashboardData(){
    this.http.get(environment.apiUrl+ apiLists.dashboard_tutor).subscribe({
      next:(res:any)=>{
        this.dashboardData = res['data']
        this.updateNextServiceCountdown();
      }
  })
}

  /**
   * Load every service for the calendar.
   *
   * The dashboard payload only carries *upcoming* services, so it cannot fill
   * a month the user has navigated back to. The tutor's service list covers
   * past and future alike, and its ids are what /tutor/service-dashboard/:id
   * resolves against.
   */
  private getCalendarServices(): void {
    if (!this.tutorId) {
      this.buildCalendar();
      return;
    }
    const params = new URLSearchParams();
    params.set('tutor_id', this.tutorId);
    // The API caps items_per_page at 100.
    params.set('items_per_page', '100');
    this.http.get<any>(environment.apiUrl + apiLists.servicelist + '?' + params).subscribe({
      next: response => {
        this.calendarServices = response?.data || [];
        this.buildCalendar();
      },
      error: () => {
        this.calendarServices = [];
        this.buildCalendar();
      }
    });
  }

  get calendarMonthLabel(): string {
    return new Date(this.viewYear, this.viewMonth, 1)
      .toLocaleString('default', { month: 'long', year: 'numeric' });
  }

  get isViewingCurrentMonth(): boolean {
    const today = new Date();
    return this.viewYear === today.getFullYear() && this.viewMonth === today.getMonth();
  }

  previousMonth(): void {
    this.shiftMonth(-1);
  }

  nextMonth(): void {
    this.shiftMonth(1);
  }

  goToToday(): void {
    const today = new Date();
    this.viewYear = today.getFullYear();
    this.viewMonth = today.getMonth();
    this.buildCalendar();
  }

  private shiftMonth(delta: number): void {
    // Build a Date so December -> January rolls the year over for us.
    const shifted = new Date(this.viewYear, this.viewMonth + delta, 1);
    this.viewYear = shifted.getFullYear();
    this.viewMonth = shifted.getMonth();
    this.buildCalendar();
  }

  private buildCalendar(): void {
    const today = new Date();
    const daysInMonth = new Date(this.viewYear, this.viewMonth + 1, 0).getDate();
    const startIndex = new Date(this.viewYear, this.viewMonth, 1).getDay();

    const servicesByDate = new Map<string, any[]>();
    this.calendarServices.forEach(service => {
      const key = this.serviceDateKey(service);
      if (!key) {
        return;
      }
      const bucket = servicesByDate.get(key);
      if (bucket) {
        bucket.push(service);
      } else {
        servicesByDate.set(key, [service]);
      }
    });

    const weeks: CalendarCell[][] = [];
    const blank: CalendarCell = { day: null, date: null, isToday: false, services: [] };
    let currentDay = 1;

    while (currentDay <= daysInMonth) {
      const week: CalendarCell[] = Array.from({ length: 7 }, (_, index) => {
        if (weeks.length === 0 && index < startIndex) {
          return { ...blank };
        }
        if (currentDay > daysInMonth) {
          return { ...blank };
        }

        const day = currentDay++;
        const key = this.dateKey(this.viewYear, this.viewMonth, day);
        return {
          day,
          date: new Date(this.viewYear, this.viewMonth, day),
          // Compare the whole date; matching only the day number marked the
          // same number "today" in every month.
          isToday:
            day === today.getDate() &&
            this.viewMonth === today.getMonth() &&
            this.viewYear === today.getFullYear(),
          services: (servicesByDate.get(key) || []).sort(
            (a, b) => String(a?.time || '').localeCompare(String(b?.time || ''))
          )
        };
      });
      weeks.push(week);
    }

    this.calendarWeeks = weeks;
  }

  /** Open a day's services, then go to whichever one the tutor picks. */
  openDay(cell: CalendarCell): void {
    if (!cell.day || !cell.services.length || !cell.date) {
      return;
    }
    const dialogRef = this.dialog.open<ServiceDayDialogResult>(ServiceDayDialogComponent, {
      panelClass: ['profile-drawer'],
      data: { date: cell.date, services: cell.services }
    });
    dialogRef.closed.subscribe(result => {
      const service = result?.service;
      const serviceId = service?.id || service?.service_id;
      if (serviceId) {
        this.router.navigate(['/tutor/service-dashboard', serviceId], { state: { service } });
      }
    });
  }

  private serviceDateKey(service: any): string {
    const raw = service?.date || service?.service?.date;
    if (!raw) {
      return '';
    }
    // The API sends plain YYYY-MM-DD; take it as-is so no timezone shift can
    // move a service onto the neighbouring day.
    return String(raw).slice(0, 10);
  }

  private dateKey(year: number, month: number, day: number): string {
    return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }

  getServiceRequests(): void {
    this.http.get<any>(environment.apiUrl + apiLists.get_booked_services).subscribe({
      next: response => this.serviceRequests = response?.data || [],
      error: () => this.toastr.error('Unable to load service requests.')
    });
  }

  /** The dashboard panel shows only the latest few; the rest live on their own page. */
  get recentServiceRequests(): any[] {
    return this.serviceRequests.slice(0, 5);
  }

  bookingStatus(booking: any): string {
    return String(booking?.status || booking?.booking_status || 'PENDING').toUpperCase();
  }

  pendingProposal(booking: any): any | null {
    return (booking?.reschedule_proposals || []).find((proposal: any) => proposal.proposal_status === 'PENDING') || null;
  }

  updateBooking(booking: any, action: 'accept' | 'decline'): void {
    this.http.patch(
      `${environment.apiUrl}${apiLists.cancel_booking}${booking.id}/${action}/`,
      {}
    ).subscribe({
      next: () => {
        this.toastr.success(`Service request ${action === 'accept' ? 'accepted' : 'declined'}.`);
        this.getServiceRequests();
        this.getDashboardData();
      },
      error: (error) => this.toastr.error(error?.error?.detail || 'Unable to update this request.')
    });
  }

  cancelService(booking: any): void {
    this.http.delete(
      `${environment.apiUrl}${apiLists.cancel_booking}${booking.id}/`,
      { body: {} }
    ).subscribe({
      next: () => {
        this.toastr.success('Service cancelled.');
        this.getServiceRequests();
      },
      error: (error) => this.toastr.error(error?.error?.detail || 'Unable to cancel this service.')
    });
  }

  proposeReschedule(booking: any): void {
    const dialogRef = this.dialog.open<RescheduleDialogResult>(RescheduleDialogComponent, {
      panelClass: ['profile-drawer'],
      data: {
        currentStartAt: booking?.scheduled_start_at,
        serviceName: booking?.service?.service_name
      }
    });

    dialogRef.closed.subscribe((result) => {
      if (!result?.proposedStartAt) {
        return;
      }
      this.http.post(
        `${environment.apiUrl}${apiLists.booking_reschedule}${booking.id}/reschedule/`,
        { proposed_start_at: result.proposedStartAt }
      ).subscribe({
        next: () => {
          this.toastr.success('Reschedule proposal sent.');
          this.getServiceRequests();
        },
        error: (error) => this.toastr.error(error?.error?.detail || 'Unable to propose a new time.')
      });
    });
  }

  respondToProposal(booking: any, accept: boolean): void {
    const proposal = this.pendingProposal(booking);
    if (!proposal?.id) {
      return;
    }
    const action = accept ? 'accept' : 'reject';
    this.http.patch(
      `${environment.apiUrl}${apiLists.booking_reschedule}${booking.id}/reschedule/${proposal.id}/${action}/`,
      {}
    ).subscribe({
      next: () => {
        this.toastr.success(`Reschedule proposal ${accept ? 'accepted' : 'rejected'}.`);
        this.getServiceRequests();
      },
      error: (error) => this.toastr.error(error?.error?.detail || 'Unable to respond to this proposal.')
    });
  }

  updateNextServiceCountdown(): void {
    const services = this.dashboardData?.upcoming_services || [];
    const now = new Date();
    const nextService = services
      .map((service: any) => ({
        service,
        start: service.scheduled_start_at
          ? new Date(service.scheduled_start_at)
          : new Date(`${service.date}T${service.time}`)
      }))
      .filter((item: any) => !Number.isNaN(item.start.getTime()) && item.start > now)
      .sort((first: any, second: any) => first.start.getTime() - second.start.getTime())[0];

    if (!nextService) {
      this.nextServiceCountdown = 'No upcoming services';
      return;
    }

    const minutes = Math.max(1, Math.floor((nextService.start.getTime() - now.getTime()) / 60000));
    const days = Math.floor(minutes / 1440);
    const hours = Math.floor((minutes % 1440) / 60);
    const remainingMinutes = minutes % 60;

    if (days > 0) {
      this.nextServiceCountdown = `in ${days}d ${hours}h`;
    } else if (hours > 0) {
      this.nextServiceCountdown = `in ${hours}h ${remainingMinutes}m`;
    } else {
      this.nextServiceCountdown = `in ${remainingMinutes}m`;
    }
  }

  openServiceDashboard(service: any): void {
    const serviceId = service?.id || service?.service_id || service?.booking_id;
    if (!serviceId) {
      return;
    }
    this.router.navigate(['/tutor/service-dashboard', serviceId], { state: { service } });
  }

  gotoChat(data:any){
    console.log(data);
    const tutorDATA = {
    user: {
      id: data.members[0]['user_id'],
      full_name: data.members[0]['full_name'],
      email: data.members[0]['email']
    }
  }
         const isMobile = window.innerWidth < 768;
      //    const payload = {
      //   user_id: JSON.parse(localStorage.getItem('user_id') || ''),
      //   target_user_id: data.members.at(0)?.user_id
      // };     
      let params: URLSearchParams = new URLSearchParams();
      params.set('target_user_id', data.members[0]['user_id'] || '');                         
        this.http.post(environment.apiUrl + apiLists.chat_room_creation+ '?' + params,{} ).subscribe({
          next:(res:any)=>{
            console.log(res);
             const dialogRef = this.dialog.open(ChatboxComponent, {
        height: '100%',
         width: isMobile ? '100%' : '450px',
        panelClass: 'profile-drawer',
        data: {
          tutor: tutorDATA,
          chat_id: res.chat_room_id,
          user_id: JSON.parse(localStorage.getItem('user_id') || 'null')
        }
      });
          }
        })
  }

  updateChatList(message: any): void {

    const index = this.chatlist.findIndex(room =>
        room.chat_room_id === message.chat_room_id
    );

    if(index === -1){
         this.getchatlist();
         return
    }

    this.chatlist[index].last_message = {
        id: message.id,
        sender_id: message.sender_id,
        content: message.content,
        created_at: message.created_at
    };

    const room = this.chatlist.splice(index, 1)[0];

    this.chatlist.unshift(room);

}
}
