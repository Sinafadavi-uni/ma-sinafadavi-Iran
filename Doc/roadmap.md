Phase 1: Decentralized Mapping (HRW Hashing insted of Uhashring)


rec/dtn/placement

Task 1: HRW
Task 2: Membership
Task 3: Mapper
Task 4: "hrw_select" insted of "random.choice" in broker
Task 5: datastore-cache in datastore
Task 6: Executor and Datastore send periodic-heartbeat to Broker


Phase 2: Multiple Redundant Copies (Replication)


In this phase, our focus is** not on REC as a whole**, but specifically on optimizing the data retention and replication mechanism in the Datastore layer and the Broker’s coordinating role.

• Task 1: Optimizing the Replication Scheme in Datastore
Existing Issue:
In the current version of REC, the way data replication and version management is not explicitly defined, dynamic, and resilient to network outages.
Our proposed optimization:
• Introducing Quorum-based Replication (N, W, R)
• Ensuring that each data is maintained on multiple independent nodes
• Preventing excessive data replication to preserve bandwidth in emergency situations
Result: Simultaneously increasing data availability and network stability

• Task 2: Optimizing the Broker’s role as Replication Coordinator
Existing Issue:
Broker in REC only has a simple routing and coordination role.
Suggested Optimization
• Upgrade Broker to a Replication Coordinator
• Make informed decisions about:
◦ Where to store Replicas
◦ Number of confirmations required for a write to succeed
◦ Manage temporarily offline nodes
Result: Remove implicit dependency on stable and central nodes

• Task 3: Write Path Optimization
Issue:
Writes can be incomplete or lost in network outages.
Suggested Optimization
• Send write operations to multiple Replicas in parallel
• Declare success only after receiving at least W valid responses
• Use Idempotent operations to avoid inconsistencies due to Retry
Result: Reduce latency and increase reliability of data recording in crisis situations

• Task 4: ptimize offline node management (Hinted Handoff)
Issue:
REC does not have an explicit mechanism for temporarily managing datastore node outages.
Suggested Optimization:
• Temporarily hold writes for inactive replicas
• Automatically deliver data after the node returns to the network
• Run a background reconciliation process
Result: High partition tolerance without the cost of continuous synchronization

• Task 5: Optimize the read path and detect the valid version
Existing issue:
Data reading may be done from an old replica.
Suggested Optimization:
• Use Replica Metadata to detect the updated version
• Accept the result only from the valid replica
• Provide Read Repair field
Result: Logical consistency (Eventual Consistency Control)
Summary
“In the second phase, we purposefully optimize the data storage and replication mechanism in REC. The focus is on upgrading the Datastore and Broker using Quorum-based Replication, managing offline nodes, and utilizing version metadata. These optimizations directly address one of the gaps raised in the Future Work section of the original paper and increase the stability, availability, and efficiency of REC in emergency scenarios.

























Phase 3: Efficient Incremental Recovery (Merkle Trees)


