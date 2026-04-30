export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type Evidence = {
  source: string;
  resource: string;
  namespace: string | null;
  signal: string;
  detail: string;
};

export type IncidentAssessment = {
  title: string;
  severity: Severity;
  likely_cause: string;
  affected_resources: string[];
  evidence: Evidence[];
  safe_next_steps: string[];
  unknowns: string[];
};

export type ClusterAssessment = {
  summary: string;
  severity: Severity;
  incidents: IncidentAssessment[];
  evidence_count: number;
  unknowns: string[];
};

export const sampleAssessment: ClusterAssessment = {
  summary: '5 candidate incidents, highest severity: high',
  severity: 'high',
  evidence_count: 17,
  unknowns: ['CloudWatch latency traces are not connected in this local studio run.'],
  incidents: [
    {
      title: 'Pod/checkout-api-7c9d4f-8x2ps is unhealthy',
      severity: 'high',
      likely_cause: "missing required env var STRIPE_API_KEY",
      affected_resources: ['Pod/checkout-api-7c9d4f-8x2ps', 'Deployment/checkout-api'],
      evidence: [
        {
          source: 'pod_status',
          resource: 'Pod/checkout-api-7c9d4f-8x2ps',
          namespace: 'payments',
          signal: 'CrashLoopBackOff',
          detail: 'container restarted 17 times in 18m'
        },
        {
          source: 'logs',
          resource: 'Pod/checkout-api-7c9d4f-8x2ps',
          namespace: 'payments',
          signal: 'recent_logs',
          detail: 'fatal: missing required env var STRIPE_API_KEY'
        },
        {
          source: 'k8sgpt',
          resource: 'Pod/checkout-api-7c9d4f-8x2ps',
          namespace: 'payments',
          signal: 'finding',
          detail: 'Container exits before readiness probe can succeed'
        }
      ],
      safe_next_steps: [
        'kubectl describe pod checkout-api-7c9d4f-8x2ps -n payments',
        'kubectl logs checkout-api-7c9d4f-8x2ps -n payments --tail=100',
        'kubectl describe deployment checkout-api -n payments'
      ],
      unknowns: []
    },
    {
      title: 'Service/checkout-api has endpoint readiness risk',
      severity: 'high',
      likely_cause: 'Service has no ready endpoints',
      affected_resources: ['Service/checkout-api', 'Endpoints/checkout-api'],
      evidence: [
        {
          source: 'endpoints',
          resource: 'Service/checkout-api',
          namespace: 'payments',
          signal: 'endpoint_readiness',
          detail: 'ready=0 not_ready=1'
        }
      ],
      safe_next_steps: [
        'kubectl get endpoints checkout-api -n payments -o wide',
        'kubectl describe service checkout-api -n payments'
      ],
      unknowns: []
    },
    {
      title: 'Node/ip-10-0-42-18 is not ready',
      severity: 'high',
      likely_cause: 'Node status is NotReady',
      affected_resources: ['Node/ip-10-0-42-18'],
      evidence: [
        {
          source: 'node_status',
          resource: 'Node/ip-10-0-42-18',
          namespace: null,
          signal: 'NotReady',
          detail: 'taints=[node.kubernetes.io/not-ready], pod_count=31'
        }
      ],
      safe_next_steps: [
        'kubectl describe node ip-10-0-42-18',
        'kubectl get pods -A --field-selector spec.nodeName=ip-10-0-42-18'
      ],
      unknowns: []
    },
    {
      title: 'PVC/checkout-cache is not bound',
      severity: 'medium',
      likely_cause: 'PVC status is Pending',
      affected_resources: ['PVC/checkout-cache'],
      evidence: [
        {
          source: 'pvc_status',
          resource: 'PVC/checkout-cache',
          namespace: 'payments',
          signal: 'Pending',
          detail: 'storage_class=gp3 capacity=None'
        }
      ],
      safe_next_steps: ['kubectl describe pvc checkout-cache -n payments'],
      unknowns: []
    }
  ]
};

export const timeline = [
  { time: '12:04:18', label: 'Deployment rollout began', severity: 'info' },
  { time: '12:06:43', label: 'First checkout-api restart observed', severity: 'medium' },
  { time: '12:08:12', label: 'Service endpoints dropped to zero ready targets', severity: 'high' },
  { time: '12:11:49', label: 'K8sGPT surfaced environment variable failure', severity: 'high' },
  { time: '12:14:03', label: 'Node health regression correlated with pending cache volume', severity: 'medium' }
] as const;

export const severityOrder: Record<Severity, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1
};
