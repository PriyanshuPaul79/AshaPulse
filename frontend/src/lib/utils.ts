import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(isoString: string) {
  const date = new Date(isoString);
  const now = new Date();
  const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);

  if (diffInHours < 24) {
    if (diffInHours < 1) {
      const mins = Math.floor(diffInHours * 60);
      return mins <= 0 ? 'Just now' : `${mins} mins ago`;
    }
    return `${Math.floor(diffInHours)} hours ago`;
  }
  if (diffInHours < 48) {
    return 'Yesterday';
  }
  return date.toLocaleDateString();
}

export function truncate(text: string, length: number) {
  if (text.length <= length) return text;
  return text.slice(0, length) + "...";
}
