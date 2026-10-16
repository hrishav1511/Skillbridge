import { Dialog } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { Subject, Subscription, map, debounceTime, distinctUntilChanged, filter, tap, switchMap } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { apiLists } from '../../../resources/apiLists';
import { ChatboxComponent } from '../../../resources/Modals/chatbox/chatbox.component';
import { FavoriteItem, ServiceItem, ServiceListResponse } from '../../../resources/models';
import { LoadingServiceService } from '../../../resources/services/loading-service.service';
import { FavoritesService } from '../../../resources/services/favorites.service';
import { BookServiceComponent } from '../../../resources/Modals/book-service/book-service.component';
import { ChatRoomService } from '../../../resources/services/chat-room.service';
import { ToastrService } from 'ngx-toastr';
@Component({
  selector: 'app-service-list',
  templateUrl: './service-list.component.html',
  styleUrls: ['./service-list.component.scss']
})
export class ServiceListComponent {
services: ServiceItem[] = [];
  loading = false;
  error: string | null = null;
  searchError: string | null = null;
  searchQuery = '';
  selectedSort = 'newest';
  minPrice: number | null = null;
  maxPrice: number | null = null;
  readonly sortOptions = [
    { value: 'newest', label: 'Newest' },
    { value: 'date:asc', label: 'Earliest service date' },
    { value: 'rating:desc', label: 'Rating: high to low' },
    { value: 'rating:asc', label: 'Rating: low to high' },
    { value: 'price:asc', label: 'Price: low to high' },
    { value: 'price:desc', label: 'Price: high to low' },
    { value: 'availability', label: 'Availability' }
  ];

  /* Filter + pagination state, all applied server-side. */
  selectedProgram = '';
  academicPrograms: string[] = [];
  page = 1;
  totalPages = 1;
  totalRecords = 0;
  readonly itemsPerPage = 12;

  private searchSubject = new Subject<string>();
  private searchSubscription!: Subscription;
  loggedInUser: any;

  constructor(
    private http: HttpClient,
    private dialog: Dialog,
    private route: Router,
    private loadingservice: LoadingServiceService,
    private favoritesService: FavoritesService,
    private chatRooms: ChatRoomService,
    private toastr: ToastrService
  ) {
    this.loggedInUser=JSON.parse(localStorage.getItem('userData')|| '{}')
  }

  ngOnInit(): void {
    this.loadAcademicPrograms();

    /*
     * One pipeline for every load. Search ran through this subject while
     * sort, filter and page changes fired their own uncancelled http.get, so
     * the two raced and a slower plain request could overwrite a searched
     * result set with an unfiltered one. switchMap means the newest request
     * always wins.
     */
    this.searchSubscription = this.searchSubject.pipe(
      debounceTime(250),
      switchMap(() => {
        this.loading = true;
        this.error = null;
        return this.http.get<ServiceListResponse>(this.buildSearchUrl(this.searchQuery));
      })
    ).subscribe({
      next: (response) => {
        this.services = response?.data || [];
        this.applyMetadata(response);
        this.loading = false;
      },
      error: (error) => {
        this.error = error?.error?.message || 'Failed to load services. Please try again.';
        this.loading = false;
      }
    });

    this.getData();
  }

  private buildSearchUrl(query?: string): string {
    // NOTE: swap `apiLists.tutorlist` for your services endpoint if it differs.
    const baseUrl = environment.apiUrl + apiLists.servicelist;
    const trimmed = query?.trim();
    const params = new URLSearchParams({ sort: this.selectedSort });

    if (trimmed) {
      params.set('query', trimmed);
    }
    if (this.minPrice !== null && this.minPrice !== undefined) {
      params.set('min_price', String(this.minPrice));
    }
    if (this.maxPrice !== null && this.maxPrice !== undefined) {
      params.set('max_price', String(this.maxPrice));
    }
    if (this.selectedProgram) {
      // Services carry no program of their own; the API matches the tutor's.
      params.set('academic_program', this.selectedProgram);
    }

    params.set('page', String(this.page));
    params.set('items_per_page', String(this.itemsPerPage));

    return `${baseUrl}?${params.toString()}`;
  }

  onSortChange(sort: string): void {
    this.selectedSort = sort;
    this.page = 1;
    this.getData(this.searchQuery);
  }

  onProgramChange(program: string): void {
    this.selectedProgram = program;
    this.page = 1;
    this.getData(this.searchQuery);
  }

  applyPriceFilter(): void {
    this.page = 1;
    this.getData(this.searchQuery);
  }

  clearPriceFilter(): void {
    this.minPrice = null;
    this.maxPrice = null;
    this.page = 1;
    this.getData(this.searchQuery);
  }

  clearFilters(): void {
    this.selectedProgram = '';
    this.minPrice = null;
    this.maxPrice = null;
    this.selectedSort = 'newest';
    this.page = 1;
    this.getData(this.searchQuery);
  }

  get hasActiveFilters(): boolean {
    return !!this.selectedProgram
      || this.minPrice !== null
      || this.maxPrice !== null
      || this.selectedSort !== 'newest';
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages || page === this.page) {
      return;
    }
    this.page = page;
    this.getData(this.searchQuery);
  }

  /** Filter options come from the whole visible tutor set, not this page. */
  private loadAcademicPrograms(): void {
    this.http.get<{ data: string[] }>(environment.apiUrl + apiLists.academic_programs)
      .subscribe({
        next: response => this.academicPrograms = response?.data || [],
        error: () => this.academicPrograms = []
      });
  }

  private applyMetadata(response: any): void {
    const metadata = response?.metadata || {};
    this.totalPages = Number(metadata.total_page) || 1;
    this.totalRecords = Number(metadata.total_records) || 0;
    this.page = Number(metadata.current_page) || this.page;
  }

  /** Ask the pipeline for a fresh page with the current state. */
  getData(searchTerm?: string): void {
    if (searchTerm !== undefined) {
      this.searchQuery = searchTerm;
    }
    this.searchSubject.next(this.searchQuery);
  }

  onSearch(value: string): void {
    const query = (value ?? '').trim();
    this.searchQuery = query;
    this.searchError = null;
    this.page = 1;

    if (!query) {
      this.searchSubject.next('');
      return;
    }

    if (query.length > 40) {
      this.searchError = 'Search text cannot exceed 40 characters.';
      return;
    }
    if (!/^[A-Za-z0-9@.\s-]+$/.test(query)) {
      this.searchError = 'Use only letters, numbers, spaces, hyphens, @, or periods.';
      return;
    }

    this.searchSubject.next(query);
  }

  getAvatarUrl(service: ServiceItem): string | null {
    return service.tutor?.profile_image ?? null;
  }

  isFavorite(service: ServiceItem): boolean {
    return this.favoritesService.isFavorite('Service', service.id);
  }

  toggleFavorite(service: ServiceItem, event: Event): void {
    event.stopPropagation();
    const favoriteValue = !this.isFavorite(service);
    const favorite: FavoriteItem = {
      id: service.id,
      type: 'Service',
      title: service.service_name,
      subtitle: `by ${service.tutor.full_name}`,
      imageUrl: this.getThumbnailUrl(service),
      metadata: `${this.formatDate(service.date)} · ${this.formatTime(service.time)}`,
      item: service
    };
    this.http.put(
      `${environment.apiUrl}${apiLists.service_fav}${service.id}/`,
      { favorite: favoriteValue }
    ).subscribe({
      next: () => {
        if (favoriteValue) {
          this.favoritesService.toggle(favorite);
        } else {
          this.favoritesService.remove('Service', service.id);
        }
        this.favoritesService.notifyChanged('Service');
      },
      error: (error) => console.error('Error updating service favourite:', error)
    });
  }

  getThumbnailUrl(service: ServiceItem): string | null {
    if (Array.isArray(service.image_urls) && service.image_urls.length > 0) {
      return service.image_urls[0] ?? null;
    }

    return this.getAvatarUrl(service);
  }

  handleImageError(event: Event): void {
    const target = event.target as HTMLImageElement | null;
    if (!target) {
      return;
    }

    target.style.display = 'none';
    const parent = target.parentElement;
    if (parent) {
      const fallback = parent.querySelector('.service-card__initial') as HTMLElement | null;
      if (fallback) {
        fallback.style.display = 'flex';
      }
    }
  }

  getInitial(service: ServiceItem): string {
    return (service.tutor?.full_name || '')
      .split(' ')
      .map((name: string) => name.charAt(0))
      .slice(0, 2)
      .join('')
      .toUpperCase();
  }

  formatLevel(level: string): string {
    if (!level) return '';
    return level.charAt(0).toUpperCase() + level.slice(1).toLowerCase();
  }

  levelClass(level: string): string {
    return 'level--' + (level || '').toLowerCase();
  }

  formatDate(date: string): string {
    if (!date) return '';
    const d = new Date(date);
    if (isNaN(d.getTime())) return date;
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }

  formatTime(time: string): string {
    if (!time) return '';
    const [hStr, mStr] = time.split(':');
    let h = parseInt(hStr, 10);
    if (isNaN(h)) return time;
    const suffix = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    return `${h}:${mStr ?? '00'} ${suffix}`;
  }

  trackById(_index: number, item: ServiceItem): string {
    return item.id;
  }

  joinService(service: ServiceItem, event?: Event): void {
    event?.stopPropagation();
    if (service.joining_link) {
      window.open(service.joining_link, '_blank', 'noopener,noreferrer');
    }
  }

  openChat(service: ServiceItem, event?: Event): void {
    event?.stopPropagation();
    const isMobile = window.innerWidth < 768;

    this.chatRooms.createDirectRoom(service.tutor_user_id ?? service.tutor?.id).subscribe({
      next: (res) => {
        this.dialog.open(ChatboxComponent, {
          height: '100%',
          width: isMobile ? '100%' : '450px',
          panelClass: 'profile-drawer',
          data: {
            tutor: service.tutor,
            chat_id: res.chat_room_id,
            user_id: JSON.parse(localStorage.getItem('user_id') || 'null')
          }
        });
      },
      error: (error) => this.toastr.error(this.chatRooms.failureMessage(error))
    });
  }

  bookService(item:any){
    let dialog = this.dialog.open(BookServiceComponent, {
      height: '100%',
      panelClass: 'profile-drawer',
      data: item,
    })

    dialog.closed.subscribe((result: any) => {
      if(result){
        this.getData()
      }
    });
  }

  ngOnDestroy(): void {
    this.searchSubscription?.unsubscribe();
  }
}
