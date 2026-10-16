import { Dialog } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { map, debounceTime, distinctUntilChanged, filter, tap, switchMap, Subject, Subscription } from 'rxjs';
import { LoadingServiceService } from '../../../resources/services/loading-service.service';
import { environment } from '../../../../environments/environment';
import { apiLists } from '../../../resources/apiLists';
import { ChatboxComponent } from '../../../resources/Modals/chatbox/chatbox.component';
import { TutorListResponse, TutorProfile, FavoriteItem } from '../../../resources/models';
import { FavoritesService } from '../../../resources/services/favorites.service';
import { ChatRoomService } from '../../../resources/services/chat-room.service';
import { ToastrService } from 'ngx-toastr';
@Component({
  selector: 'app-tutor-list',
  templateUrl: './tutor-list.component.html',
  styleUrls: ['./tutor-list.component.scss']
})
export class TutorListComponent implements OnInit, OnDestroy {
  tutors: TutorProfile[] = [];
  loading = false;
  error: string | null = null;
  searchError: string | null = null;
  searchQuery = '';
  selectedSort = 'newest';
  readonly sortOptions = [
    { value: 'newest', label: 'Newest' },
    { value: 'rating:desc', label: 'Rating: high to low' },
    { value: 'rating:asc', label: 'Rating: low to high' },
    { value: 'availability', label: 'Availability' }
  ];

  /* Filter + pagination state, all applied server-side. */
  selectedProgram = '';
  academicPrograms: string[] = [];
  selectedTag = '';
  tutorTags: string[] = [];
  page = 1;
  totalPages = 1;
  totalRecords = 0;
  readonly itemsPerPage = 12;

  private searchSubject = new Subject<string>();
  private searchSubscription!: Subscription;
  loggedInUser: any;
  constructor(
     private http: HttpClient, private dialog:Dialog, private route:Router,
         private loadingservice:LoadingServiceService,
         private favoritesService: FavoritesService,
         private chatRooms: ChatRoomService,
         private toastr: ToastrService
  ){
    this.loggedInUser = JSON.parse(localStorage.getItem('userData') || '{}');
  }

  ngOnInit(): void {
    this.loadFilterOptions();

    /*
     * One pipeline for every load.
     *
     * Search used to run through this subject while sort, filter and page
     * changes fired their own uncancelled http.get. The two raced, so a
     * slower plain request could land after a search and overwrite the
     * results with an unfiltered set - which is what made search and filter
     * look like they were not being applied together. Routing everything
     * through one switchMap means the newest request always wins and any
     * older one in flight is cancelled.
     */
    this.searchSubscription = this.searchSubject.pipe(
      debounceTime(250),
      switchMap(() => {
        this.loading = true;
        this.error = null;
        return this.http.get<TutorListResponse>(this.buildSearchUrl(this.searchQuery));
      })
    ).subscribe({
      next: (response) => {
        this.tutors = response?.data || [];
        this.applyMetadata(response);
        this.loading = false;
      },
      error: (error) => {
        this.error = error?.error?.message || 'Failed to load tutors. Please try again.';
        this.loading = false;
      }
    });

    this.requestReload();
  }

  /** Ask the pipeline for a fresh page with the current state. */
  private requestReload(): void {
    this.searchSubject.next(this.searchQuery);
  }

  private buildSearchUrl(query?: string): string {
    const baseUrl = environment.apiUrl + apiLists.tutorlist;
    const trimmed = query?.trim();
    const params = new URLSearchParams({ sort: this.selectedSort });

    if (trimmed) {
      params.set('query', trimmed);
    }

    if (this.selectedProgram) {
      params.set('academic_program', this.selectedProgram);
    }

    if (this.selectedTag) {
      params.set('tag', this.selectedTag);
    }

    params.set('page', String(this.page));
    params.set('items_per_page', String(this.itemsPerPage));

    return `${baseUrl}?${params.toString()}`;
  }

  onSortChange(sort: string): void {
    this.selectedSort = sort;
    this.page = 1;
    this.requestReload();
  }

  onProgramChange(program: string): void {
    this.selectedProgram = program;
    this.page = 1;
    this.requestReload();
  }

  onTagChange(tag: string): void {
    this.selectedTag = tag;
    this.page = 1;
    this.requestReload();
  }

  clearFilters(): void {
    this.selectedProgram = '';
    this.selectedTag = '';
    this.selectedSort = 'newest';
    this.page = 1;
    this.requestReload();
  }

  get hasActiveFilters(): boolean {
    return !!this.selectedProgram || !!this.selectedTag || this.selectedSort !== 'newest';
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages || page === this.page) {
      return;
    }
    this.page = page;
    this.requestReload();
  }

  /**
   * Load the filter options.
   *
   * These come from dedicated endpoints rather than the loaded tutors,
   * otherwise a program or subject whose only tutors sit on a later page
   * could never be selected.
   */
  private loadFilterOptions(): void {
    this.http.get<{ data: string[] }>(environment.apiUrl + apiLists.academic_programs)
      .subscribe({
        next: response => this.academicPrograms = response?.data || [],
        error: () => this.academicPrograms = []
      });

    this.http.get<{ data: string[] }>(environment.apiUrl + apiLists.tutor_tags)
      .subscribe({
        next: response => this.tutorTags = response?.data || [],
        error: () => this.tutorTags = []
      });
  }

  getData(searchTerm?: string): void {
    if (searchTerm !== undefined) {
      this.searchQuery = searchTerm;
    }
    this.requestReload();
  }

  private applyMetadata(response: any): void {
    const metadata = response?.metadata || {};
    this.totalPages = Number(metadata.total_page) || 1;
    this.totalRecords = Number(metadata.total_records) || 0;
    this.page = Number(metadata.current_page) || this.page;
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

  getAvatarUrl(tutor: TutorProfile): string | null {
    return tutor.user.profile_image ?? tutor.profile_picture_url ?? null;
  }

  isFavorite(tutor: TutorProfile): boolean {
    return this.favoritesService.isFavorite('Tutor', tutor.id);
  }

  toggleFavorite(tutor: TutorProfile, event: Event): void {
    event.stopPropagation();
    const favoriteValue = !this.isFavorite(tutor);
    const favorite: FavoriteItem = {
      id: tutor.id,
      type: 'Tutor',
      title: tutor.user.full_name,
      subtitle: tutor.academic_program || tutor.teaching_style || 'Tutor',
      imageUrl: this.getAvatarUrl(tutor),
      metadata: tutor.accepting_requests ? 'Available now' : 'Currently busy',
      item: tutor
    };
    this.http.put(
      `${environment.apiUrl}${apiLists.tutor_fav}${tutor.id}/`,
      { favorite: favoriteValue }
    ).subscribe({
      next: () => {
        if (favoriteValue) {
          this.favoritesService.toggle(favorite);
        } else {
          this.favoritesService.remove('Tutor', tutor.id);
        }
        this.favoritesService.notifyChanged('Tutor');
      },
      error: (error) => console.error('Error updating tutor favourite:', error)
    });
  }

  ngOnDestroy(): void {
    this.searchSubscription?.unsubscribe();
  }
  getInitial(tutor:any){
  return tutor.user.full_name
                      ?.split(' ')
                      .map((name:String) => name.charAt(0))
                      .slice(0, 2)
                      .join('')
                      .toUpperCase()
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

gotoTutor(tutor:any){
  this.route.navigateByUrl(`student/dashboard/view-tutor/${tutor.id}`)
}
}
