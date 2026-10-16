import { NgModule , CUSTOM_ELEMENTS_SCHEMA} from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { DialogModule } from '@angular/cdk/dialog';
import { OverlayModule } from '@angular/cdk/overlay';
import { AppRoutingModule } from './app-routing.module';
import { ReportDialogComponent } from './resources/Modals/report-dialog/report-dialog.component';
import { RescheduleDialogComponent } from './resources/Modals/reschedule-dialog/reschedule-dialog.component';
import { ServiceDayDialogComponent } from './resources/Modals/service-day-dialog/service-day-dialog.component';
import { AppComponent } from './app.component';
import { MyDetailsCardComponent } from './resources/Modals/my-details-card/my-details-card.component';
import { LoadingComponent } from './resources/Modals/loading/loading.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HTTP_INTERCEPTORS, HttpClientModule } from '@angular/common/http';
import { ChatboxComponent } from './resources/Modals/chatbox/chatbox.component';
import { ServiceCardComponent } from './resources/Modals/service-card/service-card.component';
import { ToastrModule } from 'ngx-toastr';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ImageCropperModule } from 'ngx-image-cropper';
import { AuthInterceptor } from './resources/services/auth.interceptor';
import { BookServiceComponent } from './resources/Modals/book-service/book-service.component';
import { ReviewsComponent } from './resources/Modals/reviews/reviews.component';
import { NotificationPopupComponent } from './resources/notification-popup/notification-popup.component';
import { AttachmenttsComponent } from './resources/Modals/attachmentts/attachmentts.component';
@NgModule({
  declarations: [
    AppComponent,
    MyDetailsCardComponent,
    LoadingComponent,
    ChatboxComponent,
    ServiceCardComponent,
    BookServiceComponent,
    ReviewsComponent,
    NotificationPopupComponent,
    AttachmenttsComponent,
    ReportDialogComponent,
    RescheduleDialogComponent,
    ServiceDayDialogComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    DialogModule,
    OverlayModule,
    ReactiveFormsModule,
    HttpClientModule,
    FormsModule,
    BrowserAnimationsModule,
    ToastrModule.forRoot({
      positionClass:'toast-top-right',
      preventDuplicates:true,
      progressBar:true,
      timeOut:3000
    }),
    ImageCropperModule
  ],
  providers: [
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    }
  ],
  bootstrap: [AppComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class AppModule { }
