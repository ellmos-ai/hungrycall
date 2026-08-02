# Initial EU AI Act assessment: HungryCall

**Date:** 2 August 2026
**Scope:** AI-assisted restaurant calls for ordering, pickup, or reservations
**Notice:** This is a technical and editorial initial assessment, not legal advice. Before live operation, the specific operator must obtain legal review of the use case, contracts, data sources, and applicable jurisdictions.

## Executive finding

HungryCall's documented intended purpose is not one of the high-risk use cases in Annex III. Article 50(1) and (5) of Regulation (EU) 2024/1689 is nevertheless directly relevant: the natural person answering the call must be clearly informed, no later than the first interaction, that they are interacting with an AI system. That rule applies from 2 August 2026.

The code starts the task with “automated assistant”. This is a useful transparency measure, but it does not yet demonstrate compliance. It does not expressly say “AI”, is not marked for verbatim delivery, and the returned call evidence is not checked to establish that it was the first bot utterance. Article 50 evidence is therefore **open and must be closed before further live calls**.

Article 50 does not answer whether obtaining the phone number, dialling it, and processing the conversation were lawful. Those preceding questions remain separate under the GDPR and, where applicable, national communications, unfair-competition, and criminal law.

## 1. Applicable duties

| Issue | Initial assessment | Reason |
| --- | --- | --- |
| AI Act Article 50(1), (5) | **Applies.** | The system is intended to interact directly by voice with natural persons. The notice must be clear and distinguishable and provided no later than the first interaction. The operator should not rely on an allegedly “obvious” synthetic voice. |
| AI Act Article 4 | **Applies by role.** | Providers and deployers must take measures supporting AI literacy for staff and other persons operating the system. Here this includes release control, monitoring, escalation, and call privacy. |
| AI Act Article 6 and Annex III | **Not high-risk for the current intended purpose.** | Restaurant orders and reservations are not listed in Annex III, and HungryCall is not a safety component of an Annex I product. |
| Article 53 / GPAI Code of Practice | **No direct project duty evidenced.** | The repository does not provide its own general-purpose AI model; it integrates a calling service. Model-provider duties must not be confused with this downstream application's duties. |
| GDPR | **Applies to personal data.** | A phone number, name, voice, conversation, callback number, and transcript can be personal data. Articles 5 and 6, and Articles 13 or 14 depending on the source, must be assessed for the contact and conversation. |

Classification depends on intended purpose. Any later repurposing for employment assessment, educational access, creditworthiness, or another Annex III use requires a new assessment before use. Regulation (EU) 2026/1744 moved the Annex III high-risk requirements to 2 December 2027; Article 50 applies independently and applies now.

## 2. What the code does and does not establish

### Existing controls

- `hungrycall/engine.py:49-55` builds the canonical task and begins it with `Hello, I am an automated assistant calling on behalf of ...`.
- The phrase precedes the substantive task in delivery, pickup, and reservation modes (`hungrycall/engine.py:58-103`).
- The live adapter sends that task, the destination number, and `locale: de` to CALL-E (`hungrycall/call_client.py:392-426`).
- A real call requires both `--live` and `--confirm-live` (`hungrycall/cli.py:24-29, 111-120`). This prevents accidental dispatch; it is not a legal basis or a recipient notice.
- The result can contain a masked transcript and activity (`hungrycall/call_client.py:447-479`), which could support an evidence check.

### Open Article 50 gap

The present sentence says “automated assistant”, not expressly “AI system”. It is also outside quotation marks. The repository's own measured findings in `FINDINGS.md` state that unquoted task text may be paraphrased or extended by the service. The result path does not check whether the notice was spoken or whether it was the first bot utterance.

The status is therefore **partially implemented, compliance not demonstrated**. A robust minimum would be a verbatim, localised first sentence such as:

> “Hello, I am an AI call assistant acting on behalf of [name].”

It must precede the order, price question, or any other substance in every live path. Result validation should inspect the first bot utterance and mark a call non-compliant if disclosure is absent or late. These items are recorded in `AUFGABEN.txt`; this assessment does not claim they already exist.

## 3. The called person did not consent in advance

The app user's instruction does not automatically cover the restaurant worker who answers. Consent during the conversation cannot retrospectively authorise prior collection of the number, its disclosure to CALL-E, or dialling.

Before a live call, the controller must document at least:

1. **Purpose and legal basis by phase:** obtaining the number, selecting it, dialling, speaking, transcribing, local storage, and provider retention are separate processing operations. Reliance on GDPR Article 6(1)(f) requires an actual legitimate-interests assessment, including reasonable expectations and less intrusive alternatives. A publicly listed business number is not a blanket permission.
2. **Privacy information:** if the number was not obtained from the person, Article 14 must be assessed, normally with information at first communication. Answers collected directly during the call also engage Article 13. In addition to the AI notice, the first layer should identify the controller, purpose, number source, transcription or recording, rights, and an accessible full notice.
3. **Objection and suppression:** a refusal, hang-up, or objection must be respected immediately and reflected in a purpose-limited suppression list. Cascade logic must not redial the same person after a merely technical failure.
4. **Separate advertising classification:** placing a genuine order or reservation is not automatically telephone advertising. If a particular deployment is advertising, German UWG section 7 applies as well; use of an automatic calling machine for advertising requires prior express consent under section 7(2)(2).
5. **Recording assessment:** the repository proves receipt of a transcript, not whether or how the service stores audio. If audio is recorded, authority to do so must be assessed separately in advance; German Criminal Code section 201 protects non-public spoken words. “No local audio” is insufficient if a service provider records it.

The statement in `SPEC.md` that published restaurant numbers are intended to receive calls is a product assumption, not an established legal basis. Restaurant employees retain data-protection and personality rights.

## 4. Hosting duties by server mode

The roles of AI Act provider and deployer and GDPR controller or processor follow from actual purposes, means, contracts, and branding—not a server-mode label. A party offering HungryCall under its own brand or putting it into service must document the role allocation under AI Act Article 3 and GDPR Article 4.

| Mode in `../huckepack/KONZEPT.md` | Consequence |
| --- | --- |
| `local` | The operator holds the local database and key. Access control, retention, rights handling, logs, contracts, and complete privacy information are required. The current multi-user readiness finding is negative (`HOST-READINESS.md:3-30`). |
| `huckepack-gift` | Browser persistence reduces durable host storage, not host involvement. The host provides the key and execution; call data pass through its process. Disclosure, legal basis, CALL-E terms, transfers, deletion, and rights handling remain necessary. |
| `huckepack-only-host` | A visitor-owned key does not automatically neutralise the host's legal role. Data and the key transit the host for the call; role allocation, security, and onward disclosure must be documented. |
| `pay-membership` | The concept is a stub only. Accounts, tenant isolation, billing, object authorisation, secret management, deletion, export, incident handling, and full compliance operations are prerequisites. It must not be represented as ready. |

`DATA-FLOW.md:22-33, 37-65` evidences the transfer of the destination and task to CALL-E, missing contractual evidence about provider retention and transfers, and continued transit processing in piggyback modes. `PRIVACY-TEMPLATE.md:25-71` deliberately leaves operator facts open; completing a template does not implement them.

### Release criteria before live hosting

- A fixed first AI sentence in every language and path, with automated evidence from the first bot utterance.
- Documented role, purpose, and legal-basis matrix, including number source and legitimate-interests assessment where relied upon.
- Concise spoken first-layer information and a full accessible Articles 13/14 notice.
- Verified CALL-E contracting entity, roles, subprocessors, countries, retention, deletion route, Article 28 terms, and any Chapter V mechanism.
- Separate decision on transcription and possible audio recording; minimisation, retention, access, deletion, objection, and suppression procedures.
- Security and tenant review appropriate to the mode; `pay-membership` remains blocked until built.
- Article 4 AI-literacy measures and a documented reassessment on every purpose change.

## 5. Sources and evidence limits

This assessment builds on, but does not reproduce, the following in-house Um:bruch analyses:

- `C:\Users\User\OneDrive\.TOPICS\.UMBRUCH\website\src\content\blog\ai-act-transparenzpflichten-ab-august-2026.md` — “From 2 August: recognising AI content is no longer a side issue”.
- `...\ki-reviews\eu-ai-act-transparenz-code-of-practice.md` and adjacent `eu-ai-act-transparency-code-of-practice.md`.
- `...\ki-reviews\eu-ai-act-haftungsluecke.md` and adjacent `eu-ai-act-liability-gap.md`.
- `C:\Users\User\OneDrive\.TOPICS\.UMBRUCH\_editorial\entwuerfe\2026-07-03_eu-ai-act_leitartikel_synthese.md`, treated as an editorial draft, not a published source.

Primary and authority sources: [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj), [Digital Omnibus Regulation (EU) 2026/1744](https://eur-lex.europa.eu/eli/reg/2026/1744/oj), [AI Act Article 50 explorer](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50), [implementation timeline](https://ai-act-service-desk.ec.europa.eu/en/ai-act/timeline/timeline-implementation-eu-ai-act), [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/2016-05-04/eng), [German UWG section 7](https://www.gesetze-im-internet.de/uwg_2004/__7.html), and [German Criminal Code section 201](https://www.gesetze-im-internet.de/stgb/__201.html).

Current CALL-E contractual facts, actual audio recording, provider retention, processing countries, subprocessors, and the specific operator's legal basis are not evidenced and remain open.
