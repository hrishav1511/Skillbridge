import { Component, OnDestroy, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, filter, map, switchMap, tap } from 'rxjs/operators';
import { apiLists } from '../../resources/apiLists'
import { environment } from '../../../environments/environment';
import { ChatboxComponent } from '../../resources/Modals/chatbox/chatbox.component';
import { Dialog } from '@angular/cdk/dialog';
import {
  ServiceDayDialogComponent,
  ServiceDayDialogResult
} from '../../resources/Modals/service-day-dialog/service-day-dialog.component';
import { Route, Router } from '@angular/router';
import { LoadingServiceService } from '../../resources/services/loading-service.service';
import { ChatMessage, FavoriteItem, FavoriteType } from '../../resources/models';
import { FavoritesService } from '../../resources/services/favorites.service';
import { ChatService } from '../../resources/services/socket.service';
import { ChatRoomService } from '../../resources/services/chat-room.service';
import { ToastrService } from 'ngx-toastr';
interface CalendarCell {
  day: number | null;
  date: Date | null;
  isToday: boolean;
  bookings?: any[];
}

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit, OnDestroy {
  currentMonth = '';
  currentYear = 0;
  /*
   * The month on screen. buildCalendar() used to read new Date() directly,
   * which pinned the grid to the present month with no way to move off it.
   */
  viewYear = new Date().getFullYear();
  viewMonth = new Date().getMonth();
  weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  calendarWeeks: CalendarCell[][] = [];
  loggedInUser: any | null;
  chatlist: any[] = [];
  selectedlistype: String = 'Tutor'
  student_ID: any = localStorage.getItem('student_id');
  booked_service_list: any = []
  today = new Date();
  DashbopardData: any = {}
  selectedFavoriteType: FavoriteType = 'Tutor';
  favoriteItems: FavoriteItem[] = [];
  favoritesLoading = false;
  private messageSubscription?: Subscription;
  constructor(private http: HttpClient, private dialog: Dialog, private route: Router,
    private loadingservice: LoadingServiceService,
    private favoritesService: FavoritesService,
    private toastr: ToastrService,
    private chatService: ChatService,
    private chatRooms: ChatRoomService
  ) {
    this.loggedInUser = JSON.parse(localStorage.getItem('userData') || '{}')
    console.log('user ==>', this.loggedInUser);
  }

  ngOnInit(): void {
    this.messageSubscription = this.chatService.newMessage$.subscribe(message => this.updateChatList(message));
    this.favoritesService.favoriteChanged$.subscribe((type) => this.loadFavorites(type));
    // this.getData();
    if (this.loggedInUser['role'] !== 'guest' ) {

      this.getBookings()
      this.getDashboardData()
      this.getchatlist()
     this.loadFavorites(this.selectedFavoriteType);

    }
    console.log('user ==>', this.loggedInUser);


  }

  ngOnDestroy(): void {
    this.messageSubscription?.unsubscribe();
  }

  selectedListType(key: String) {
    this.selectedlistype = key
  }

  selectFavoriteType(type: FavoriteType): void {
    this.selectedFavoriteType = type;
    this.loadFavorites(type);
  }

  private loadFavorites(type: FavoriteType): void {
    this.favoritesLoading = true;
    const params = new URLSearchParams({ favorite_only: 'true' });
    const endpoint = type === 'Tutor' ? apiLists.tutorlist : apiLists.servicelist;

    this.http.get<any>(`${environment.apiUrl}${endpoint}?${params.toString()}`).subscribe({
      next: (response) => {
        const items = response?.data || [];
        this.favoriteItems = type === 'Tutor'
          ? items.map((tutor: any): FavoriteItem => ({
              id: tutor.id,
              type: 'Tutor',
              title: tutor.user?.full_name || 'Tutor',
              subtitle: tutor.academic_program || tutor.teaching_style || 'Tutor',
              imageUrl: tutor.user?.profile_image || tutor.profile_picture_url,
              metadata: tutor.accepting_requests ? 'Available now' : 'Currently busy',
              item: tutor
            }))
          : items.map((service: any): FavoriteItem => ({
              id: service.id,
              type: 'Service',
              title: service.service_name || 'Service',
              subtitle: `by ${service.tutor?.full_name || 'Tutor'}`,
              imageUrl: service.image_urls?.[0] || service.tutor?.profile_image,
              metadata: `${service.date || ''} · ${(service.time || '').slice(0, 5)}`,
              item: service
            }));
        this.favoritesService.replaceType(type, this.favoriteItems);
        this.favoriteItems = this.favoritesService.favorites;
        this.favoritesLoading = false;
      },
      error: (error) => {
        console.error('Error fetching favourites:', error);
        this.favoriteItems = [];
        this.favoritesLoading = false;
      }
    });
  }

  get selectedFavorites(): FavoriteItem[] {
    return this.favoriteItems.filter((favorite) => favorite.type === this.selectedFavoriteType);
  }

  removeFavorite(favorite: FavoriteItem): void {
    const endpoint = favorite.type === 'Tutor' ? apiLists.tutor_fav : apiLists.service_fav;
    this.http.put(
      `${environment.apiUrl}${endpoint}${favorite.id}/`,
      { favorite: false }
    ).subscribe({
      next: () => {
        this.favoritesService.remove(favorite.type, favorite.id);
        this.toastr.success('Removed from favourites.');
        this.loadFavorites(favorite.type);
      },
      error: (error) => console.error('Error removing favourite:', error)
    });
  }

  openFavorite(favorite: FavoriteItem): void {
    if (favorite.type === 'Tutor') {
      this.route.navigateByUrl(`student/dashboard/view-tutor/${favorite.id}`);
    }
  }



private buildCalendar(): void {
  const today = new Date();

  this.currentMonth = new Date(this.viewYear, this.viewMonth, 1)
    .toLocaleString('default', { month: 'long' });
  this.currentYear = this.viewYear;

  const daysInMonth = new Date(this.viewYear, this.viewMonth + 1, 0).getDate();
  const startIndex = new Date(this.viewYear, this.viewMonth, 1).getDay();

  const weeks: CalendarCell[][] = [];
  const blank: CalendarCell = { day: null, date: null, isToday: false, bookings: [] };

  let currentDay = 1;

  while (currentDay <= daysInMonth) {

    const week: CalendarCell[] = Array.from(
      { length: 7 },
      (_, index) => {

        // Padding before the first day and after the last.
        if (weeks.length === 0 && index < startIndex) {
          return { ...blank };
        }

        if (currentDay > daysInMonth) {
          return { ...blank };
        }

        const cellDay = currentDay;

        const dateString = this.formatDate(
          this.viewYear,
          this.viewMonth,
          cellDay
        );
        const dayBookings = this.booked_service_list.filter(
          (booking:any) => this.bookingDate(booking) === dateString
        );

        // Compare the whole date. Matching only the day number marked the
        // same number as "today" in every month.
        const isToday =
          cellDay === today.getDate() &&
          this.viewMonth === today.getMonth() &&
          this.viewYear === today.getFullYear();

        currentDay++;

        return {
          day: cellDay,
          date: new Date(this.viewYear, this.viewMonth, cellDay),
          isToday,
          bookings: dayBookings
        };
      }
    );

    weeks.push(week);
  }

  this.calendarWeeks = weeks;
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
  // Going through a Date rolls the year over at the December/January edge.
  const shifted = new Date(this.viewYear, this.viewMonth + delta, 1);
  this.viewYear = shifted.getFullYear();
  this.viewMonth = shifted.getMonth();
  this.buildCalendar();
}

private formatDate(
  year: number,
  month: number,
  day: number
): string {

  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

/**
 * Open the services booked on a day, then go to the bookings page.
 *
 * This used to only log the cell to the console, so clicking a date did
 * nothing visible. Students have no per-service route, so a selection lands on
 * the booked-services list rather than a detail page.
 */
daydetails(cell: CalendarCell): void {
  if (!cell?.day || !cell.date || !cell.bookings?.length) {
    return;
  }
  const dialogRef = this.dialog.open<ServiceDayDialogResult>(ServiceDayDialogComponent, {
    panelClass: ['profile-drawer'],
    data: { date: cell.date, services: cell.bookings }
  });
  dialogRef.closed.subscribe(result => {
    if (result?.service) {
      this.route.navigate(['/student/booked-services']);
    }
  });
}

  getBookings() {
    let params: URLSearchParams = new URLSearchParams()
    params.set('student_id', this.student_ID)
    params.set('items_per_page', '3')
    this.http.get(environment.apiUrl + apiLists.get_booked_services + '?' + params).subscribe({
      next: (res: any) => {
        this.booked_service_list = res['data']
        this.buildCalendar();

      },
      error: (err: any) => {
        console.log(err)
        this.buildCalendar();

      },
      complete:()=>{
        console.log("Bookings fetched successfully")
      }
    })
  }

  getInitials(fullName: string | undefined): string {
    if (!fullName) {
      return '';
    }

    const parts = fullName.trim().split(/\s+/);
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }

    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  openChat(tutor: any): void {
    const isMobile = window.innerWidth < 768;

    this.chatRooms.createDirectRoom(tutor?.user?.id).subscribe({
      next: (res) => {
        const dialogRef = this.dialog.open(ChatboxComponent, {
          height: '100%',
          width: isMobile ? '100%' : '450px',
          panelClass: 'profile-drawer',

          data: {
            tutor: tutor,
            chat_id: res.chat_room_id,
            user_id: JSON.parse(localStorage.getItem('user_id') || 'null')
          }
        });
        dialogRef.closed.subscribe(() => {
          this.getchatlist();
        });
      },
      error: (error) => this.toastr.error(this.chatRooms.failureMessage(error))
    });
  }

  openChatfromList(data: any): void {
    const isMobile = window.innerWidth < 768;
    const payload = {
      user_id: JSON.parse(localStorage.getItem('user_id') || 'null'),
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
        user_id: JSON.parse(localStorage.getItem('user_id') || 'null')
      }
    });

  }


  getchatlist() {

    // this.loadingservice.setLoading()
    let params: URLSearchParams = new URLSearchParams()
    params.set('user_id', JSON.parse(localStorage.getItem('user_id') ?? 'null'))
    this.http.get(environment.apiUrl + apiLists.chat_room_list + '?' + params).subscribe({
      next: (res: any) => {
        this.chatlist = res.slice(0, 3).filter((x: any) => x.last_message);
        // this.loadingservice.setSuccess()
      },
      error: (err: any) => {
        console.log(err)
        // this.loadingservice.setError()
      }
    })
  }

  private updateChatList(message: ChatMessage): void {
    const index = this.chatlist.findIndex((room: any) => room.chat_room_id === message.chat_room_id);
    if (index < 0) {
      this.getchatlist();
      return;
    }

    const room = {
      ...this.chatlist[index],
      last_message: message
    };
    this.chatlist = [room, ...this.chatlist.filter((_: unknown, roomIndex: number) => roomIndex !== index)].slice(0, 3);
  }

  formatTime(time: string): string {

    if (!time) return '';

    const [hours, minutes] = time.split(':').map(Number);

    const date = new Date();

    date.setHours(hours, minutes);

    return date.toLocaleTimeString([], {
      hour: 'numeric',
      minute: '2-digit'
    });

  }

  pastDateCheck(date: String | any) {
    return new Date(date) > this.today
  }

  isServiceEnded(item: any): boolean {
    const service = item?.service;
    const scheduledStart = item?.scheduled_start_at
      ? new Date(item.scheduled_start_at)
      : service?.date
        ? new Date(`${service.date}T${service.time || '00:00:00'}`)
        : null;
    if (!scheduledStart || Number.isNaN(scheduledStart.getTime())) {
      return false;
    }

    const duration = this.serviceDurationMs(service);
    return scheduledStart.getTime() + duration <= Date.now();
  }

  private bookingDate(booking: any): string | undefined {
    if (booking?.scheduled_start_at) {
      const scheduled = new Date(booking.scheduled_start_at);
      if (!Number.isNaN(scheduled.getTime())) {
        return this.formatDate(
          scheduled.getFullYear(),
          scheduled.getMonth(),
          scheduled.getDate()
        );
      }
    }
    return booking?.service?.date;
  }

  private serviceDurationMs(service: any): number {
    if (!service?.time || !service?.end_time) {
      return 0;
    }
    const [startHours, startMinutes] = service.time.split(':').map(Number);
    const [endHours, endMinutes] = service.end_time.split(':').map(Number);
    return Math.max(0, (endHours * 60 + endMinutes - startHours * 60 - startMinutes) * 60000);
  }

  getDashboardData(){
    let params: URLSearchParams = new URLSearchParams()
    params.set('user_id', JSON.parse(localStorage.getItem('user_id') ?? 'null'))
    this.http.get(environment.apiUrl + apiLists.dashboard_student + '?' + params).subscribe({
      next:(res:any)=>{
        console.log('Dashboard data:', res);
        this.DashbopardData = res['data']
      },
      error:(err:any)=>{
        console.error('Error fetching dashboard data:', err);
      }
    })
  }


  gotohats() {
    this.route.navigateByUrl('student/chats')
  }
  goToServices(){
    this.route.navigateByUrl('student/booked-services')
  }

  openBookedService(item: any): void {
    const serviceId = item?.id || item?.booking_id || item?.service?.id;
    this.route.navigate(['/student/booked-services'], {
      queryParams: serviceId ? { serviceId } : undefined
    });
  }
}
