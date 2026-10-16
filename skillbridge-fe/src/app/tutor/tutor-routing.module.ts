import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TutorDashboardComponent } from './tutor-dashboard/tutor-dashboard.component';
import { MyProfileComponent } from './my-profile/my-profile.component';
import { TutorComponent } from './tutor.component';
import { TutorChatComponent } from './tutor-chat/tutor-chat.component';
import { ServiceDashboardComponent } from './service-dashboard/service-dashboard.component';
import { TutorServicesComponent } from './services/tutor-services.component';
import { ServiceDetailsComponent } from './services/service-details.component';
import { NotificationTrayComponent } from '../resources/notification-tray/notification-tray.component';
import { ServiceRequestsComponent } from './service-requests/service-requests.component';
import { RoleGuard } from '../resources/guards/role.guard';
const routes: Routes = [
  {
    path: '',
    component: TutorComponent,
    canActivate: [RoleGuard],
    data: { roles: ['TUTOR'] },
    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      },
      {
        path: 'dashboard',
        component: TutorDashboardComponent
      },
      {
        path: 'my-profile',
        component: MyProfileComponent
      },
       {
        path: 'my-messages',
        component: TutorChatComponent
      },
      {
        path: 'notifications',
        component: NotificationTrayComponent
      },
      {
        path: 'service-dashboard/:serviceId',
        component: ServiceDashboardComponent
      },
      {
        path: 'service-requests',
        component: ServiceRequestsComponent
      },
      {
        // Old paths kept as redirects so links from before the
        // service -> service rename still work.
        path: 'service-dashboard/:serviceId',
        redirectTo: 'service-dashboard/:serviceId'
      },
      {
        path: 'service-requests',
        redirectTo: 'service-requests',
        pathMatch: 'full'
      },
      {
        path: 'services',
        component: TutorServicesComponent
      },
      {
        path: 'services/:serviceId',
        component: ServiceDetailsComponent
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class TutorRoutingModule { }
