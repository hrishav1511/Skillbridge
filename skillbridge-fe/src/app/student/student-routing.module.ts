import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard.component';
import { ChatListComponent } from './chat-list/chat-list.component';
import { StudentComponent } from './student/student.component';
import { ViewTutorComponent } from './view-tutor/view-tutor.component';
import { ServicesListComponent } from './services-list/services-list.component';
import { PaymentPortalComponent } from './payment-portal/payment-portal.component';
import { NotificationTrayComponent } from '../resources/notification-tray/notification-tray.component';
import { RoleGuard } from '../resources/guards/role.guard';

const routes: Routes = [
  {
    path: '',
    component: StudentComponent,
    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      },
      {
        path: 'dashboard',
        component: DashboardComponent,
        canActivate: [RoleGuard],
        data: { roles: ['STUDENT'], allowGuest: true }
      },
      {
        path: 'chats',
        component: ChatListComponent,
        canActivate: [RoleGuard],
        data: { roles: ['STUDENT'] }
      },
      {
        path: 'notifications',
        component: NotificationTrayComponent,
        canActivate: [RoleGuard],
        data: { roles: ['STUDENT'] }
      },
      {
        path:'dashboard/view-tutor/:id',
        component:ViewTutorComponent,
        canActivate: [RoleGuard],
        data: { roles: ['STUDENT'], allowGuest: true }
      },
      {
        path:'booked-services',
        component:ServicesListComponent,
        canActivate: [RoleGuard],
        data: { roles: ['STUDENT'] }
      },
      {
        // Old path kept as a redirect so existing links and bookmarks from
        // before the service -> service rename still land somewhere.
        path:'booked-services',
        redirectTo:'booked-services',
        pathMatch:'full'
      },
      {
        path:'payment/:id',
        component:PaymentPortalComponent,
        canActivate: [RoleGuard],
        data: { roles: ['STUDENT'] }
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class StudentRoutingModule { }
