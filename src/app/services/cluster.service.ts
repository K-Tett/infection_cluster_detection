import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// NOTE: Interface matching the backend API response structure
export interface ClustersByInfection {
  [key: string]: string[][];
}

@Injectable({
  providedIn: 'root'
})
export class ClusterService {
  private readonly apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  /**
   * Uploads transfers and microbiology CSV files to the backend
   */
  uploadFiles(transfersFile: File, microbiologyFile: File): Observable<{ message: string }> {
    const formData = new FormData();
    formData.append('files', transfersFile, transfersFile.name);  
    formData.append('files', microbiologyFile, microbiologyFile.name);

    return this.http.post<{ message: string }>(`${this.apiUrl}/upload/`, formData);
  }

  /**
   * Retrieves detected clusters from the backend
   */
  getClusters(): Observable<ClustersByInfection> {
    return this.http.get<ClustersByInfection>(`${this.apiUrl}/clusters/`);
  }
}