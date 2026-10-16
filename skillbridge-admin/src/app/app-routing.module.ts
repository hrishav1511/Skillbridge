import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './login/login.component';

const routes: Routes = [
  {path:'' , redirectTo:'auth',pathMatch:'full'},
  {path:'auth', loadChildren:()=> import('./login/login.module').then(m=> m.LoginModule) },
  {path:'panel', loadChildren:()=> import('./layout/layout.module').then(m=> m.LayoutModule) }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
