import { ChangeDetectionStrategy, Component, computed, signal, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import * as d3 from 'd3';
import { ClusterService, ClustersByInfection } from './services/cluster.service';

// --- TYPE DEFINITIONS for D3 Visualization ---
// Our custom Node properties, extending D3's simulation node type.
// This interface now correctly inherits optional properties like x, y, fx, fy
// once @types/d3 is installed.
interface Node extends d3.SimulationNodeDatum {
  id: string;
  infection: string;
}

// D3's link type, connecting our custom Node objects
type Link = d3.SimulationLinkDatum<Node>;


// NOTE: Mock data removed - now using real backend API calls

// --- COMPONENT-SPECIFIC TYPE DEFINITIONS ---
interface Cluster {
  id: string;
  infection: string;
  patientCount: number;
  patients: string[];
}

// NOTE: ClustersByInfection interface moved to cluster.service.ts


@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  // --- STATE MANAGEMENT ---
  files = signal<{ transfers: File | null, microbiology: File | null }>({ transfers: null, microbiology: null });
  currentView = signal<'table' | 'list'>('table');
  clusters = signal<Cluster[]>([]);
  isLoading = signal<boolean>(false);
  error = signal<string | null>(null);
  selectedCluster = signal<Cluster | null>(null);
  selectedNode = signal<Node | null>(null);
  analyzerResponse = signal<string>('');
  selectedAnalysisType = signal<string>('');

  // --- PAGINATION STATE ---
  currentPage = signal(1);
  itemsPerPage = signal(6);

  // --- COMPUTED SIGNALS ---
  totalPages = computed(() => {
    const totalItems = this.clusters().length;
    return Math.ceil(totalItems / this.itemsPerPage());
  });

  paginatedClusters = computed(() => {
    const allClusters = this.clusters();
    const page = this.currentPage();
    const itemsPerPage = this.itemsPerPage();
    const startIndex = (page - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return allClusters.slice(startIndex, endIndex);
  });

  // --- LIFECYCLE & EFFECTS ---
  constructor(private clusterService: ClusterService) {
    // NOTE: Graph renders whenever clusters data changes, not tied to view
    effect(() => {
      if (this.clusters().length > 0) {
        // Timeout to ensure the DOM is ready for D3
        setTimeout(() => this.renderGraph(this.clusters()), 100);
      }
    });

    // NOTE: Handle window resize for graph responsiveness
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', () => {
        if (this.clusters().length > 0) {
          setTimeout(() => this.renderGraph(this.clusters()), 100);
        }
      });
    }
  }

  // --- UI EVENT HANDLERS ---
  onFileSelect(event: Event, fileType: 'transfers' | 'microbiology'): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      this.files.update(currentFiles => ({...currentFiles, [fileType]: input.files![0]}));
    }
  }

  async handleUpload(): Promise<void> {
      if (!this.files().transfers || !this.files().microbiology) {
          this.error.set("Both files must be selected.");
          return;
      }
      this.isLoading.set(true);
      this.error.set(null);

      try {
        // NOTE: Real backend API integration - upload files then get clusters
        console.log('Uploading files to backend...');
        await this.clusterService.uploadFiles(
          this.files().transfers!, 
          this.files().microbiology!
        ).toPromise();

        console.log('Fetching detected clusters...');
        const result = await this.clusterService.getClusters().toPromise();
        
        if (result) {
          const formattedClusters = this.formatApiData(result);
          this.clusters.set(formattedClusters);
          this.currentPage.set(1);
        } else {
          throw new Error('No cluster data received from backend');
        }
      } catch (e) {
        console.error('Backend API error:', e);
        this.error.set(`Failed to process cluster data: ${e instanceof Error ? e.message : 'Unknown error'}`);
        this.clusters.set([]);
      } finally {
        this.isLoading.set(false);
      }
  }

  setView(view: 'table' | 'list'): void {
    this.currentView.set(view);
  }

  // --- CLUSTER & NODE SELECTION ---
  selectCluster(cluster: Cluster): void {
    this.selectedCluster.set(cluster);
    // Clear node selection when selecting different cluster
    this.selectedNode.set(null);
    // NOTE: Clear analyzer response and selection when switching clusters
    this.analyzerResponse.set('');
    this.selectedAnalysisType.set('');
  }

  selectNode(node: Node): void {
    this.selectedNode.set(node);
  }

  clearSelection(): void {
    this.selectedNode.set(null);
  }

  // --- RISK CALCULATION METHODS ---
  getRiskLevel(node: Node): string {
    const connections = this.getNodeConnections(node);
    if (connections >= 5) return 'High';
    if (connections >= 3) return 'Medium';
    return 'Low';
  }

  getRiskLevelClass(node: Node): string {
    const level = this.getRiskLevel(node);
    return `risk-${level.toLowerCase()}`;
  }

  getNodeConnections(node: Node): number {
    // Count how many other patients this node is connected to across all clusters
    let connections = 0;
    this.clusters().forEach(cluster => {
      if (cluster.patients.includes(node.id)) {
        connections += cluster.patients.length - 1; // -1 to exclude self
      }
    });
    return connections;
  }

  // --- NODE COLOR CALCULATION ---
  private getNodeColor(node: Node): string {
    const connections = this.getNodeConnections(node);
    const maxConnections = Math.max(...this.clusters().map(c => c.patients.length));
    const ratio = connections / maxConnections;
    
    // NOTE: Green to red gradient based on connection ratio
    if (ratio <= 0.33) return '#10b981'; // green-500
    if (ratio <= 0.66) return '#f59e0b'; // yellow-500
    return '#ef4444'; // red-500
  }

  // --- LLM ANALYZER ---
  onAnalyzerFilterChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    const filterType = select.value;
    
    // NOTE: Update selected analysis type signal
    this.selectedAnalysisType.set(filterType);
    
    if (!filterType) {
      this.analyzerResponse.set('');
      return;
    }
    
    if (!this.selectedCluster()) {
      this.analyzerResponse.set('');
      return;
    }

    // NOTE: Mock LLM response for now - replace with actual API call
    const cluster = this.selectedCluster()!;
    let response = '';

    switch (filterType) {
      case 'cluster_id':
        response = `Cluster ${cluster.id} contains ${cluster.patientCount} patients with ${cluster.infection} infection. This cluster represents a significant outbreak requiring immediate attention and isolation protocols.`;
        break;
      case 'size':
        response = `This ${cluster.infection} cluster involves ${cluster.patientCount} patients. ${cluster.patientCount > 5 ? 'Large cluster size indicates high transmission risk.' : 'Moderate cluster size suggests contained transmission.'}`;
        break;
      case 'location':
        response = `${cluster.infection} cluster detected across multiple ward locations. Geographic spread suggests possible nosocomial transmission requiring enhanced infection control measures.`;
        break;
      case 'timeframe':
        response = `${cluster.infection} cluster timeframe spans multiple days with overlapping patient stays. Temporal clustering indicates active transmission period requiring immediate intervention.`;
        break;
      case 'significance':
        response = `High significance cluster: ${cluster.patientCount} patients with ${cluster.infection}. Recommend immediate isolation, contact tracing, and enhanced cleaning protocols.`;
        break;
    }

    this.analyzerResponse.set(response);
  }

  // --- PAGINATION LOGIC ---
  nextPage(): void {
    if (this.currentPage() < this.totalPages()) {
      this.currentPage.update(page => page + 1);
    }
  }

  prevPage(): void {
    if (this.currentPage() > 1) {
      this.currentPage.update(page => page - 1);
    }
  }
  
  // --- DATA FORMATTING ---
  private formatApiData(data: ClustersByInfection): Cluster[] {
    let allClusters: Cluster[] = [];
    let clusterCounter = 1;
    for (const infection in data) {
      const clustersForInfection = data[infection];
      for (const patientList of clustersForInfection) {
        allClusters.push({
          id: `C${clusterCounter++}`,
          infection: infection,
          patients: patientList,
          patientCount: patientList.length,
        });
      }
    }
    return allClusters;
  }
  
  // --- D3 GRAPH RENDERING ---
  private renderGraph(clustersData: Cluster[]): void {
    const graphContainer = d3.select("#graph-container");
    graphContainer.selectAll("*").remove();

    if (clustersData.length === 0) return;
    
    // 1. Transform data for D3 - Create nodes and links from cluster data
    const nodes: Node[] = [];
    const links: Link[] = [];
    const patientToNode = new Map<string, Node>();

    // NOTE: Build nodes from all unique patients across clusters
    clustersData.forEach(cluster => {
        cluster.patients.forEach(patientId => {
            if (!patientToNode.has(patientId)) {
                const newNode: Node = { id: patientId, infection: cluster.infection };
                patientToNode.set(patientId, newNode);
                nodes.push(newNode);
            }
        });

        // Create links between patients in same cluster (Obsidian-style connections)
        for (let i = 0; i < cluster.patients.length; i++) {
            for (let j = i + 1; j < cluster.patients.length; j++) {
                links.push({
                    source: patientToNode.get(cluster.patients[i])!,
                    target: patientToNode.get(cluster.patients[j])!,
                });
            }
        }
    });

    // 2. Setup SVG and dimensions with fallback
    const containerElement = graphContainer.node() as HTMLElement;
    const width = containerElement.clientWidth || 800;
    const height = containerElement.clientHeight || 600;
    
    const svg = graphContainer.append("svg")
        .attr("viewBox", [0, 0, width, height])
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("preserveAspectRatio", "xMidYMid meet")
        .style("background", "radial-gradient(circle at 50% 50%, #1e293b 0%, #0f172a 100%)");

    // NOTE: Create zoom group to contain all graph elements for zoom/pan functionality
    const zoomGroup = svg.append("g")
        .attr("class", "zoom-group");

    // NOTE: Define zoom behavior with scale limits and smooth transitions
    const zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 5]) // Min 0.1x, Max 5x zoom
        .on("zoom", (event) => {
            zoomGroup.attr("transform", event.transform);
        });

    // Apply zoom behavior to SVG
    svg.call(zoomBehavior);

    // 3. Initialize Force Simulation with Obsidian-like forces
    const simulation = d3.forceSimulation<Node>(nodes)
        .force("link", d3.forceLink<Node, Link>(links).id((d: Node) => d.id).distance(80))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(25))
        .on("tick", ticked);

    // 4. Create links with subtle styling (now inside zoom group)
    const link = zoomGroup.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke", "#475569")
        .attr("stroke-opacity", 0.4)
        .attr("stroke-width", 1);

    // 5. Create node groups with interaction (now inside zoom group)
    const nodeGroups = zoomGroup.append("g")
        .attr("class", "nodes")
        .selectAll<SVGGElement, Node>("g")
        .data(nodes)
        .join("g")
        .style("cursor", "pointer")
        .call(this.drag(simulation))
        // NOTE: Prevent node drag from interfering with zoom/pan
        .on("mousedown.zoom", null)
        .on("click", (event, d) => {
            event.stopPropagation();
            this.selectNode(d);
        })
        .on("mouseover", (event, d) => {
            // Highlight connected nodes and links
            this.highlightConnections(d, nodeGroups, link, true);
        })
        .on("mouseout", (event, d) => {
            // Remove highlighting
            this.highlightConnections(d, nodeGroups, link, false);
        });

    // 6. Add circles with gradient colors based on risk
    nodeGroups.append("circle")
        .attr("r", (d: Node) => {
            const connections = this.getNodeConnections(d);
            return Math.max(8, Math.min(15, 8 + connections * 0.5)); // Size based on connections
        })
        .attr("fill", (d: Node) => this.getNodeColor(d))
        .attr("stroke", "#e2e8f0")
        .attr("stroke-width", 2)
        .attr("filter", "drop-shadow(0 2px 4px rgba(0,0,0,0.3))");

    // 7. Add patient ID labels
    nodeGroups.append("text")
        .text((d: Node) => d.id)
        .attr("x", 0)
        .attr("y", 0)
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "middle")
        .attr("fill", "#ffffff")
        .style("font-size", "8px")
        .style("font-weight", "600")
        .style("text-shadow", "0 1px 2px rgba(0,0,0,0.8)")
        .style("pointer-events", "none");

    // 8. Add infection type labels below nodes
    nodeGroups.append("text")
        .text((d: Node) => d.infection)
        .attr("x", 0)
        .attr("y", 20)
        .attr("text-anchor", "middle")
        .attr("fill", "#94a3b8")
        .style("font-size", "7px")
        .style("pointer-events", "none");

    // 9. Ticked function to update positions
    function ticked() {
        link
            .attr("x1", (d: Link) => (d.source as Node).x!)
            .attr("y1", (d: Link) => (d.source as Node).y!)
            .attr("x2", (d: Link) => (d.target as Node).x!)
            .attr("y2", (d: Link) => (d.target as Node).y!);

        nodeGroups
            .attr("transform", (d: Node) => `translate(${d.x},${d.y})`);
    }

    // NOTE: Auto-fit functionality - calculate bounds and fit all nodes in view
    const autoFit = () => {
        if (nodes.length === 0) return;
        
        // Wait for simulation to settle before calculating bounds
        setTimeout(() => {
            const bounds = {
                minX: d3.min(nodes, d => d.x || 0) || 0,
                maxX: d3.max(nodes, d => d.x || 0) || 0,
                minY: d3.min(nodes, d => d.y || 0) || 0,
                maxY: d3.max(nodes, d => d.y || 0) || 0
            };
            
            const padding = 50;
            const graphWidth = bounds.maxX - bounds.minX + padding * 2;
            const graphHeight = bounds.maxY - bounds.minY + padding * 2;
            const centerX = (bounds.minX + bounds.maxX) / 2;
            const centerY = (bounds.minY + bounds.maxY) / 2;
            
            // Calculate scale to fit graph with padding
            const scale = Math.min(
                width / graphWidth,
                height / graphHeight,
                1 // Don't zoom in beyond 100%
            );
            
            // Calculate translation to center the graph
            const translateX = width / 2 - centerX * scale;
            const translateY = height / 2 - centerY * scale;
            
            // Apply transform with smooth transition
            const transform = d3.zoomIdentity
                .translate(translateX, translateY)
                .scale(scale);
                
            svg.transition()
                .duration(750)
                .call(zoomBehavior.transform, transform);
        }, 1000); // Wait for simulation to settle
    };
    
    // NOTE: Trigger auto-fit after simulation starts
    autoFit();

    // NOTE: Clear selection when clicking empty space (background click detection)
    // Handle clicks on the zoom group background
    zoomGroup.append("rect")
        .attr("width", width)
        .attr("height", height)
        .attr("fill", "transparent")
        .style("pointer-events", "all")
        .on("click", () => {
            this.clearSelection();
        });
  }

  // --- NODE HIGHLIGHTING HELPER ---
  private highlightConnections(targetNode: Node, nodeGroups: any, links: any, highlight: boolean): void {
    // Get connected node IDs
    const connectedIds = new Set<string>();
    this.clusters().forEach(cluster => {
        if (cluster.patients.includes(targetNode.id)) {
            cluster.patients.forEach(patientId => {
                if (patientId !== targetNode.id) {
                    connectedIds.add(patientId);
                }
            });
        }
    });

    // Style nodes
    nodeGroups.selectAll("circle")
        .attr("opacity", (d: any) => {
            if (!highlight) return 1;
            return d.id === targetNode.id || connectedIds.has(d.id) ? 1 : 0.3;
        })
        .attr("stroke-width", (d: any) => {
            if (!highlight) return 2;
            return d.id === targetNode.id ? 4 : connectedIds.has(d.id) ? 3 : 2;
        });

    // Style links
    links.attr("opacity", (d: any) => {
        if (!highlight) return 0.4;
        const sourceId = (d.source as Node).id;
        const targetId = (d.target as Node).id;
        return (sourceId === targetNode.id || targetId === targetNode.id) ? 0.8 : 0.1;
    })
    .attr("stroke-width", (d: any) => {
        if (!highlight) return 1;
        const sourceId = (d.source as Node).id;
        const targetId = (d.target as Node).id;
        return (sourceId === targetNode.id || targetId === targetNode.id) ? 2 : 1;
    });
  }
  
  // --- DRAG BEHAVIOR ---
  // NOTE: Updated drag behavior to work correctly with zoom/pan functionality
  private drag(simulation: d3.Simulation<Node, undefined>) {
    function dragstarted(event: d3.D3DragEvent<SVGGElement, Node, Node>, d: Node) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }
    
    function dragged(event: d3.D3DragEvent<SVGGElement, Node, Node>, d: Node) {
      d.fx = event.x;
      d.fy = event.y;
    }
    
    function dragended(event: d3.D3DragEvent<SVGGElement, Node, Node>, d: Node) {
      if (!event.active) simulation.alphaTarget(0);
      // NOTE: Keep nodes fixed after dragging for better user control
      d.fx = event.x;
      d.fy = event.y;
    }
    
    return d3.drag<SVGGElement, Node>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended)
        // NOTE: Prevent drag events from triggering zoom/pan
        .filter((event) => !event.ctrlKey && !event.metaKey);
  }
}

