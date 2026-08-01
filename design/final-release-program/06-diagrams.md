# 06. Diagrams

Every node below is declared somewhere else in this dossier: as a component in
the tables of 04-technology-map.md, or as an entity in 05-data-model.md. Nothing
here introduces a name the rest of the dossier does not carry, which is the point
of writing diagrams as code rather than drawing them.

## System context: who asks, and what answers

The four surfaces a user can touch, and the one evaluator they must all agree
with. Today the guided skills and the map template each work the answer out for
themselves, which is the disagreement Loop 3 removes.

```mermaid
flowchart LR
  CommandSurface -->|asks for the next action| LifecycleEvaluator
  GuidedSkills -->|asks for the next action| LifecycleEvaluator
  MapTemplate -->|asks for the next action| LifecycleEvaluator
  LifecycleEvaluator -->|resolves the repository through| ProjectLocator
  LifecycleEvaluator -->|reads receipts from| EvidenceStore
  LifecycleEvaluator -->|reads the tier through| DesignChecks
  LifecycleEvaluator -->|returns| ProjectState
```

## Entity relationships

The same names as 05-data-model.md, deliberately. A node here that the data model
never defined would mean the two artifacts had drifted apart.

```mermaid
erDiagram
  ProjectState ||--o{ EvidenceReceipt : cites
  ProjectState ||--o{ ReviewRecord : accumulates
  ProjectState ||--o{ WorkItem : covers
  WorkItem ||--o{ EvidenceReceipt : earns
  ReviewRecord ||--o{ DecisionPackage : raises
  DecisionPackage ||--o{ Event : appends
  EvidenceReceipt ||--o| Event : appends
  OperationResult }o--|| ProjectState : renders
```

## The evidence path, and the door in it

This is confirmed defect one of the plan review, drawn. ReceiptClassifier reads
the recorded command line as a string, so a command that ran no check at all can
satisfy an obligation. Loop 2 makes EvidenceWrapper record the check kind and
makes ReceiptClassifier read that field instead.

```mermaid
flowchart LR
  EvidenceWrapper -->|writes a receipt bound to the commit| EvidenceReceipt
  EvidenceReceipt -->|is filed in| EvidenceStore
  EvidenceStore -->|is read by| ReceiptClassifier
  ReceiptClassifier -->|clears obligations in| LifecycleEvaluator
  HardGates -->|read their own evidence files from| EvidenceStore
  DecisionStore -->|writes one per FAIL or WAIVED| DecisionPackage
  Telemetry -->|appends under a lock| Event
```

## The gate battery, and what it rests on

The container view of the merge gate. The dashed relationship is the one that
does not exist yet: ConvergenceCheck cannot require a current review, because
ReviewRecord has nowhere durable to live until Loop 3 builds it.

```mermaid
flowchart TB
  HostedRunner -->|runs the workflow| GatesWorkflow
  GatesWorkflow -->|runs| DesignChecks
  GatesWorkflow -->|runs| HardGates
  GatesWorkflow -->|runs| ConvergenceCheck
  ConvergenceCheck -->|requires fresh| EvidenceReceipt
  ConvergenceCheck -.->|will require current| ReviewRecord
  HardGates -->|verdicts become| DecisionPackage
```

## Where the program's own records live

The ledger side: what the program tracks about itself, as opposed to what the
product tracks about a user's change.

```mermaid
flowchart LR
  ProgramLedger -->|declares waves and budgets for| WorkItemStore
  WorkItemStore -->|holds| WorkItem
  WorkItem -->|is fenced and closed through| TaskRegistry
  TaskRegistry -->|records its scope against| GitHistory
  WorkItem -->|earns| EvidenceReceipt
```

## Reading these

The evaluator sits at the centre of the first diagram on purpose. Every arrow
that points at it is a surface asking a question, and every arrow leaving it is
an answer. The whole of Loop 3 is the work of making those arrows real, because
today three of the four surfaces answer the question themselves instead of
asking.
