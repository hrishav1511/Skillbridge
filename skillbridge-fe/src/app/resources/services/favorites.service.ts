import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { FavoriteItem, FavoriteType } from '../models';

@Injectable({ providedIn: 'root' })
export class FavoritesService {
  private readonly favoritesSubject = new BehaviorSubject<FavoriteItem[]>(this.readFavorites());
  readonly favorites$ = this.favoritesSubject.asObservable();
  private readonly favoriteChangedSubject = new Subject<FavoriteType>();
  readonly favoriteChanged$ = this.favoriteChangedSubject.asObservable();

  get favorites(): FavoriteItem[] {
    return this.favoritesSubject.value;
  }

  isFavorite(type: FavoriteType, id: string | undefined): boolean {
    return !!id && this.favorites.some((favorite) => favorite.type === type && favorite.id === id);
  }

  toggle(favorite: FavoriteItem): void {
    const existingIndex = this.favorites.findIndex(
      (item) => item.type === favorite.type && item.id === favorite.id
    );
    const nextFavorites = [...this.favorites];

    if (existingIndex >= 0) {
      nextFavorites.splice(existingIndex, 1);
    } else {
      nextFavorites.unshift(favorite);
    }

    this.saveFavorites(nextFavorites);
  }

  remove(type: FavoriteType, id: string): void {
    this.saveFavorites(this.favorites.filter((favorite) => !(favorite.type === type && favorite.id === id)));
  }

  replaceType(type: FavoriteType, favorites: FavoriteItem[]): void {
    const otherTypeFavorites = this.favorites.filter((favorite) => favorite.type !== type);
    this.saveFavorites([...favorites, ...otherTypeFavorites]);
  }

  notifyChanged(type: FavoriteType): void {
    this.favoriteChangedSubject.next(type);
  }

  private storageKey(): string {
    return `skillbridge-favorites-${localStorage.getItem('student_id') || localStorage.getItem('user_id') || 'guest'}`;
  }

  private readFavorites(): FavoriteItem[] {
    try {
      const stored = JSON.parse(localStorage.getItem(this.storageKey()) || '[]');
      return Array.isArray(stored) ? stored : [];
    } catch {
      return [];
    }
  }

  private saveFavorites(favorites: FavoriteItem[]): void {
    localStorage.setItem(this.storageKey(), JSON.stringify(favorites));
    this.favoritesSubject.next(favorites);
  }
}