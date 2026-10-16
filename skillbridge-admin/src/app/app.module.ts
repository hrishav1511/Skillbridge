import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { DialogModule } from '@angular/cdk/dialog';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent } from './login/login.component';
import { ApprovalCardComponent } from './resources/modals/approval-card/approval-card.component';
import { HTTP_INTERCEPTORS, HttpClientModule } from '@angular/common/http';
import { ReactiveFormsModule } from '@angular/forms';
import { RejectCardComponent } from './resources/modals/reject-card/reject-card.component';
import { UserActionComponent } from './resources/modals/user-action/user-action.component';
import { AuthInterceptor } from './resources/interceptors/auth.interceptor';
import { LoadingInterceptor } from './resources/interceptors/loading.interceptor';
import { LoaderComponent } from './layout/loader/loader.component';
@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    ApprovalCardComponent,
    RejectCardComponent,
    UserActionComponent,
    LoaderComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    ReactiveFormsModule,
    DialogModule

  ],
  providers: [
    {
      provide: HTTP_INTERCEPTORS,
      useClass: LoadingInterceptor,
      multi: true
    },
      {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    }
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
