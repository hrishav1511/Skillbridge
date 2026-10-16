import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {path:'', redirectTo:'auth', pathMatch:'full'},
  {path:'auth', loadChildren: () => import('./auth/auth.module').then(m => m.AuthModule)},
  {path:'student', loadChildren: () => import('./student/student.module').then(m => m.StudentModule)},
  {path:'tutor', loadChildren: () => import('./tutor/tutor.module').then(m => m.TutorModule)},
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
