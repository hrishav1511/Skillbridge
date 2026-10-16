import { HttpClient, HttpParams } from '@angular/common/http';
import { AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import Chart from 'chart.js/auto';
import { apilists } from 'src/app/resources/ApiList';
import { environment } from 'src/environments/environment';

interface MonthlyServices {
  month: string;
  services_done: number;
}

interface DashboardData {
  total_students: number;
  total_tutors: number;
  total_services: number;
  pending_items: number;
  monthly_services_done: MonthlyServices[];
}

interface PendingTutor {
  user?: {
    full_name?: string;
    email?: string;
  };
  academic_program?: string;
}

interface TutorReport {
  id: string;
  student_id: string;
  tutor_id: string;
  reason: string;
  reporter_name?: string | null;
  tutor_name?: string | null;
  tutor_profile_picture_url?: string | null;
  reported_at?: string | null;
}

interface ServiceReport {
  id: string;
  student_id: string;
  service_id: string;
  reason: string;
  reporter_name?: string | null;
  service_name?: string | null;
  reported_at?: string | null;
}

interface ReviewReport {
  id: string;
  reporter_user_id: string;
  review_type: 'tutor' | 'service';
  review_id: string;
  reason: string;
  review_comment?: string;
  review_rating: number;
  reported_at?: string;
}

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('servicesChart') servicesChart?: ElementRef<HTMLCanvasElement>;

  dashboardData: DashboardData = {
    total_students: 0,
    total_tutors: 0,
    total_services: 0,
    pending_items: 0,
    monthly_services_done: []
  };

  pendingTutors: PendingTutor[] = [];
  tutorReports: TutorReport[] = [];
  serviceReports: ServiceReport[] = [];
  reviewReports: ReviewReport[] = [];

  private chart?: Chart;

  readonly monthsToDisplay = 12;

  constructor(
    private http: HttpClient
  ) { }

  ngOnInit(): void {
    this.getDashbaordData();
    this.getPendingTutors();
    this.getReports();
  }

  ngAfterViewInit(): void {
    this.renderServicesChart();
  }

  ngOnDestroy(): void {
    this.chart?.destroy();
  }

  getDashbaordData(): void {
    this.http.get<{ data: DashboardData }>(environment.apiUrl + apilists.dashboard).subscribe((res) => {
      this.dashboardData = {
        ...this.dashboardData,
        ...res.data,
        monthly_services_done: res.data.monthly_services_done || []
      };
      this.renderServicesChart();
    });
  }

      private getPendingTutors(): void {
      const userId = JSON.parse(localStorage.getItem('user_id') || 'null');
      const params = new HttpParams().set('user_id', String(userId ?? ''));

      this.http.get<{ data: PendingTutor[] }>(environment.apiUrl + apilists.pending_user, { params }).subscribe((res) => {
        this.pendingTutors = res.data || [];
      });
      }

  getReports(): void {
    this.http.get<{ data: TutorReport[] }>(environment.apiUrl + apilists.tutor_reports).subscribe({
      next: (res) => this.tutorReports = res.data || [],
      error: () => this.tutorReports = []
    });
    this.http.get<{ data: ServiceReport[] }>(environment.apiUrl + apilists.service_reports).subscribe({
      next: (res) => this.serviceReports = res.data || [],
      error: () => this.serviceReports = []
    });
    this.http.get<{ data: ReviewReport[] }>(environment.apiUrl + apilists.review_reports).subscribe({
      next: (res) => this.reviewReports = res.data || [],
      error: () => this.reviewReports = []
    });
  }

  get monthlyServices(): MonthlyServices[] {
    return this.dashboardData.monthly_services_done.slice(-this.monthsToDisplay);
  }

  formatMonth(month: string): string {
    const date = new Date(`${month}-01T00:00:00`);
    return date.toLocaleDateString('en-US', { month: 'short' });
  }

  get studentShare(): number {
    const total = this.dashboardData.total_students + this.dashboardData.total_tutors;
    return total ? (this.dashboardData.total_students / total) * 100 : 0;
  }

  get tutorShare(): number {
    const total = this.dashboardData.total_students + this.dashboardData.total_tutors;
    return total ? (this.dashboardData.total_tutors / total) * 100 : 0;
  }

  private renderServicesChart(): void {
    if (!this.servicesChart) {
      return;
    }

    this.chart?.destroy();
    this.chart = new Chart(this.servicesChart.nativeElement, {
      type: 'bar',
      data: {
        labels: this.monthlyServices.map((item) => this.formatMonth(item.month)),
        datasets: [{
          label: 'Completed services',
          data: this.monthlyServices.map((item) => item.services_done),
          backgroundColor: '#2b1d57',
          hoverBackgroundColor: '#7c6ae0',
          borderRadius: 6,
          borderSkipped: false,
          barPercentage: .62,
          categoryPercentage: .72
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 450
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            displayColors: false,
            callbacks: {
              label: (context) => `${context.parsed.y} completed services`
            }
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            },
            border: {
              display: false
            },
            ticks: {
              color: '#8b86a0',
              font: {
                family: 'DM Sans',
                size: 11
              }
            }
          },
          y: {
            beginAtZero: true,
            suggestedMax: Math.max(...this.monthlyServices.map((item) => item.services_done), 1),
            ticks: {
              precision: 0,
              color: '#8b86a0',
              font: {
                family: 'DM Sans',
                size: 11
              }
            },
            grid: {
              color: '#ece9f3'
            },
            border: {
              display: false,
              dash: [4, 4]
            }
          }
        }
      }
    });
  }

}
