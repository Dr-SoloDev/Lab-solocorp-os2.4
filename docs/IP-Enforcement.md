# IP Enforcement Guide

## Protecting SoloCorp OS Against Unauthorized Use, Copying, and Distribution

**Document Owner:** Legal Department (ตุลย์)
**Classification:** Internal -- Enforcement Procedure
**Last Updated:** July 2026

---

## Table of Contents

1. [Overview and Principles](#1-overview-and-principles)
2. [Discovery and Detection](#2-discovery-and-detection)
3. [Evidence Collection](#3-evidence-collection)
4. [Triage and Classification](#4-triage-and-classification)
5. [DMCA Takedown Procedure](#5-dmca-takedown-procedure)
6. [GitHub Report Process](#6-github-report-process)
7. [Course Platform Takedown Procedure](#7-course-platform-takedown-procedure)
8. [Cease and Desist Letter Process](#8-cease-and-desist-letter-process)
9. [Escalation to Legal Action](#9-escalation-to-legal-action)
10. [Templates and Forms](#10-templates-and-forms)

---

## 1. Overview and Principles

### 1.1 Purpose

This guide establishes the standard operating procedure for detecting,
investigating, and enforcing SoloCorp Organization's intellectual property
rights against unauthorized use, copying, distribution, or derivative creation
of the SoloCorp Operating System.

### 1.2 Scope

This procedure applies to all forms of infringement, including but not limited
to:

- Unauthorized forking, cloning, or redistribution of the repository
- Creation and sale of courses or tutorials based on SoloCorp OS architecture
- Commercial use without a license
- Creation of derivative works (modified versions, competing systems)
- Use of SoloCorp OS designs in competing products
- Unauthorized training of AI models on SoloCorp OS materials
- Misrepresentation or passing off as affiliated with SoloCorp

### 1.3 Core Principles

- **Act Quickly:** Time is critical. Early action reduces damage and
  strengthens legal position.
- **Document Everything:** Meticulous evidence collection is essential for
  enforcement.
- **Be Professional:** All communications should be firm, factual, and legally
  precise.
- **Escalate Deliberately:** Follow the graduated response: notice, demand,
  platform action, legal action.
- **Preserve Rights:** Never make statements that could waive or diminish
  intellectual property rights.

---

## 2. Discovery and Detection

### 2.1 Proactive Monitoring

Regularly monitor the following channels for potential infringement:

| Channel | Method | Frequency |
|---------|--------|-----------|
| GitHub | Search for forks, clones, or similar repository names | Weekly |
| Course Platforms | Search for "SoloCorp", "SoloCorp OS", "Hermes agent architecture" | Weekly |
| Google Search | Monitor for mentions and references | Monthly |
| Social Media | Monitor for posts claiming SoloCorp OS materials | Monthly |
| AI/ML Repos | Check HuggingFace, GitHub for unauthorized model training | Monthly |
| YouTube/TikTok | Search for tutorials based on SoloCorp OS | Monthly |

### 2.2 Search Queries

Use these search queries regularly to discover potential infringement:

- `"SoloCorp OS" course`
- `"SoloCorp Operating System" tutorial`
- `"SoloCorp" architecture agent multi-agent`
- `"Hermes agent" department architecture pipeline`
- `"SOUL.md" OR "agent profile" multi-agent system`
- `"agent routing" department hierarchy topology`
- `fork "Lab-solocorp-os2.4"`
- `"SoloCorp" "multi-agent" design pattern`

### 2.3 Community Reporting

Encourage community members to report suspected infringement via the
repository's Issues page. Respond to all reports within 48 hours.

---

## 3. Evidence Collection

### 3.1 What to Collect

For each suspected infringement, collect and preserve the following:

```
EVIDENCE CHECKLIST
------------------

[ ] URL(s) of infringing content
[ ] Screenshot(s) of the infringing page (full page, not cropped)
[ ] Date and time of discovery (with timezone)
[ ] Name of infringing party (if identifiable)
[ ] Platform or hosting provider information
[ ] Description of how the content infringes on SoloCorp OS IP
[ ] Comparison evidence showing original vs. infringing work
[ ] Any communication history with infringing party
[ ] Metadata (file creation dates, author information if available)
[ ] Wayback Machine archive of the infringing page (create if possible)
[ ] Download of relevant source files (if publicly accessible)
```

### 3.2 Evidence Preservation Protocol

1. Take screenshots immediately -- infringing content can disappear quickly.
2. Use a timestamp service or notarization for critical evidence.
3. Archive web pages using archive.org or a local archival tool.
4. Store all evidence in a secure, organized folder structure:
   ```
   evidence/
   ├── YYYY-MM-DD--infringer-name/
   │   ├── screenshots/
   │   ├── page-archives/
   │   ├── correspondence/
   │   └── notes.md
   ```
5. Maintain a chain of custody log for all evidence.
6. Duplicate evidence to an offsite or cloud backup.

### 3.3 Comparison Documentation

Create a side-by-side comparison document that clearly shows:

- The original SoloCorp OS element (with file path and date)
- The infringing element (with URL and date)
- Specific similarities that demonstrate copying rather than independent
  creation

---

## 4. Triage and Classification

### 4.1 Severity Levels

| Level | Criteria | Response Timeline |
|-------|----------|-------------------|
| CRITICAL | Commercial sale of courses or products based on SoloCorp OS | Immediate (24 hours) |
| HIGH | Public redistribution, public forks, competing products | 48 hours |
| MEDIUM | Derivative works, unauthorized tutorials, blog posts | 1 week |
| LOW | Attribution failures, minor unauthorized references | 2 weeks |

### 4.2 Classification Factors

Consider these factors when classifying an infringement:

- **Commercial Nature:** Is the infringer making money from the violation?
- **Scale:** How widely is the content distributed?
- **Willfulness:** Was the violation intentional or accidental?
- **Harm:** What is the potential damage to SoloCorp Organization?
- **Cooperation:** Is the infringer responsive and cooperative?

### 4.3 Response Matrix

| Severity | First Action | Second Action | Third Action |
|----------|-------------|---------------|--------------|
| CRITICAL | Cease and desist letter + DMCA notice | Platform report | File lawsuit |
| HIGH | DMCA notice + platform report | Cease and desist letter | Escalate to legal counsel |
| MEDIUM | Cease and desist letter | DMCA notice if ignored | Monitor |
| LOW | Outreach/notice | Monitor compliance | Escalate if repeated |

---

## 5. DMCA Takedown Procedure

### 5.1 When to Use DMCA

The Digital Millennium Copyright Act (DMCA) provides a mechanism to request
removal of infringing content from online platforms. Use DMCA when:

- Infringing content is hosted on a US-based platform
- The platform has a designated DMCA agent
- You have a good-faith belief that use is unauthorized
- You can provide a complete DMCA notice

### 5.2 Information Required for DMCA Notice

A valid DMCA takedown notice must include:

1. Your physical or electronic signature
2. Identification of the copyrighted work claimed to be infringed
   (reference to this repository and LICENSE file)
3. Identification of the infringing material and its location (URL)
4. Your contact information (email, address, phone)
5. A statement of good-faith belief that use is not authorized
6. A statement that the information is accurate and, under penalty of
   perjury, that you are authorized to act on behalf of the owner

### 5.3 DMCA Notice Template

Copy the following template when filing a DMCA notice.

```
----------------------------------------------------------------------
DMCA TAKEDOWN NOTICE
----------------------------------------------------------------------

To: [Platform DMCA Agent / Copyright Department]

I am writing to submit a notice of copyright infringement pursuant to
the Digital Millennium Copyright Act (17 U.S.C. Section 512(c)).

1. IDENTIFICATION OF COPYRIGHTED WORK

The copyrighted work is the SoloCorp Operating System ("SoloCorp OS"),
a multi-agent architecture and operating system owned by SoloCorp
Organization (Dr-SoloDev). The original work is located at:

https://github.com/Dr-SoloDev/Lab-solocorp-os2.4

This work is protected under copyright and is distributed under a
proprietary license that expressly prohibits unauthorized reproduction,
distribution, and derivative works.

2. IDENTIFICATION OF INFRINGING MATERIAL

The infringing material is located at:

[INSERT FULL URL(S) OF INFRINGING CONTENT]

This material infringes on the copyrighted work described above because
it [describe specifically: reproduces the architecture / is a derivative
work / includes copied code or agent prompts / redistributes protected
materials / is a course or tutorial based on the work / etc.].

3. CONTACT INFORMATION

Name: [Your Name]
Organization: SoloCorp Organization
Email: [Your Email]
Address: [Your Address]
Phone: [Your Phone]

4. GOOD FAITH STATEMENT

I have a good-faith belief that the use of the copyrighted material
described above is not authorized by the copyright owner, its agent,
or the law.

5. ACCURACY STATEMENT

The information in this notice is accurate, and under penalty of perjury,
I am authorized to act on behalf of the owner of the exclusive right
that is allegedly infringed.

6. SIGNATURE

[Your Electronic Signature]

Date: [Current Date]
----------------------------------------------------------------------
```

### 5.4 Filing Guidelines

- File against the hosting platform (GitHub, Udemy, YouTube, etc.)
- Use the platform's designated DMCA agent or submission form
- Keep a copy of the filed notice and any confirmation
- Monitor for response within 48-72 hours (statutory requirement)
- If the platform refuses, escalate to legal counsel

---

## 6. GitHub Report Process

### 6.1 Reporting Repository Infringement

To report an infringing GitHub repository:

1. Navigate to the infringing repository on GitHub.
2. Click the "Report content" link at the top of the repository page.
3. Select "Report copyright infringement."
4. Complete the form with details of the original work and infringing work.
5. Submit and retain the confirmation number.

### 6.2 DMCA via GitHub

GitHub's preferred method for copyright reports is via their DMCA form:

https://github.com/contact/dmca

GitHub also accepts DMCA notices via email at: copyright@github.com

### 6.3 Fork Policy

GitHub's Terms of Service require that forks honor the original repository's
license. If a fork continues to exist after the original repository is private
or if the license prohibits redistribution, the fork is in violation.

### 6.4 Reporting Other Violations (Non-Copyright)

GitHub also accepts reports for:

- Trademark infringement
- Impersonation
- Terms of Service violations
- Unauthorized commercial use

These can be reported at: https://support.github.com/contact/report-content

---

## 7. Course Platform Takedown Procedure

### 7.1 Common Course Platforms

| Platform | DMCA/Report Process | Contact |
|----------|---------------------|---------|
| Udemy | https://www.udemy.com/contact | Report via copyright form |
| Coursera | https://www.coursera.org/about/contact | Copyright@coursera.org |
| Skillshare | https://www.skillshare.com/contact | Legal form on website |
| Teachable | DMCA notice to legal@teachable.com | legal@teachable.com |
| LinkedIn Learning | Reporting form on platform | Copyright agent |
| YouTube | Copyright takedown tool | https://youtube.com/copyright |

### 7.2 Procedure for Course Takedown

1. **Verify:** Confirm the course uses SoloCorp OS IP without authorization.
2. **Document:** Take screenshots of course materials, descriptions, and
   enrollment information.
3. **Purchase Access:** If necessary, purchase access to document the
   infringement (document the purchase).
4. **Notice:** File a DMCA or copyright notice with the platform.
5. **Follow Up:** Check status within 7 days; escalate if ignored.
6. **Demand Accounting:** Where the course is commercial, demand an accounting
   of profits and a disgorgement of revenue received.

---

## 8. Cease and Desist Letter Process

### 8.1 When to Send

Send a cease and desist letter when:

- The infringement is documented and undeniable
- The infringer is identifiable (name and contact available)
- A graduated response is appropriate (before or alongside DMCA)
- The infringement is significant enough to warrant the effort

### 8.2 Cease and Desist Letter Template

```
----------------------------------------------------------------------
CERTIFIED CEASE AND DESIST LETTER
----------------------------------------------------------------------

Date: [Current Date]

VIA EMAIL AND CERTIFIED MAIL

To: [Infringer Name or Entity]
[Infringer Address]

RE: UNAUTHORIZED USE OF SOLOCORP OPERATING SYSTEM INTELLECTUAL PROPERTY

Dear [Infringer Name],

This firm represents SoloCorp Organization ("SoloCorp"), the sole owner
of all intellectual property rights in the SoloCorp Operating System
("SoloCorp OS").

It has come to SoloCorp's attention that you are [describe specific
infringing activity -- e.g., "offering a paid course on the SoloCorp OS
architecture," "distributing a derivative version of SoloCorp OS,"
"reproducing SoloCorp OS source code without authorization"].

Specifically, the unauthorized activity includes:

- [Description of infringing act 1]
- [Description of infringing act 2]
- [Location/URL of infringing content]

This activity infringes on SoloCorp's exclusive rights under applicable
copyright laws, trademark laws, and intellectual property treaties.
SoloCorp OS is distributed under a proprietary license (see LICENSE file
at https://github.com/Dr-SoloDev/Lab-solocorp-os2.4) that expressly
prohibits unauthorized commercial use, redistribution, derivative works,
and the creation of courses or tutorials based on its architecture.

DEMAND FOR ACTION

SoloCorp demands that you immediately:

1. CEASE AND DESIST all unauthorized use of SoloCorp OS intellectual
   property.

2. REMOVE all infringing content from all platforms and locations,
   including but not limited to [platform names, URLs].

3. PROVIDE a written confirmation within seven (7) calendar days that
   you have complied with the above demands.

4. ACCOUNT for and DISGORGE any and all profits, revenues, or other
   benefits derived from the unauthorized use of SoloCorp OS property.

FAILURE TO COMPLY

If you fail to comply with these demands within seven (7) calendar days,
SoloCorp reserves the right to pursue all available legal remedies,
including but not limited to:

- Filing a DMCA takedown notice with your hosting/platform provider
- Initiating a copyright infringement lawsuit seeking statutory damages
  of up to $150,000 per work infringed
- Seeking injunctive relief to prevent continued infringement
- Pursuing all available damages, costs, and attorneys' fees
- Reporting this violation to relevant authorities

SoloCorp prefers to resolve this matter amicably, but will not hesitate
to take aggressive action to protect its intellectual property rights.

This letter is without prejudice to SoloCorp's rights and remedies, all
of which are expressly reserved.

Sincerely,

[SoloCorp Organization Representative Name]
[Title]
SoloCorp Organization
[Contact Information]

Enclosures: [Evidence of infringement, License file, Legal notices]
----------------------------------------------------------------------
```

### 8.3 Sending Guidelines

- Send via email AND certified mail (return receipt requested)
- Use professional letterhead or formal formatting
- Include copies of evidence as enclosures
- Set a specific deadline for response (7-14 days)
- Keep copies of all correspondence
- Track delivery and response

---

## 9. Escalation to Legal Action

### 9.1 When to Escalate

Escalate to formal legal action (retained counsel and litigation) when:

- The infringer refuses to comply with a cease and desist letter
- The infringement is large-scale and commercial
- The infringement causes significant harm to SoloCorp Organization
- The infringer continues after receiving a DMCA takedown
- The infringer is domiciled in a jurisdiction with effective legal remedies

### 9.2 Preparation for Litigation

Before initiating litigation, ensure:

1. All evidence is collected, organized, and preserved
2. Copyright and trademark registrations are current (if applicable)
3. A litigation hold is in place for all relevant records
4. Potential damages have been estimated
5. Legal counsel with IP litigation experience has been retained
6. Budget for litigation has been allocated

### 9.3 Potential Claims

Legal counsel may pursue any combination of:

- Copyright infringement (17 U.S.C. Section 501 et seq.)
- Trademark infringement (15 U.S.C. Section 1114)
- False designation of origin (15 U.S.C. Section 1125(a))
- Trade dress infringement
- Unfair competition
- Misappropriation of trade secrets
- Breach of contract (where applicable)
- Conversion
- Unjust enrichment

### 9.4 Damages Available

| Claim Type | Potential Recovery |
|------------|-------------------|
| Copyright | Statutory damages up to $150,000 per work; actual damages + profits |
| Trademark | Treble damages; profits; injunctive relief |
| Trade Dress | Actual damages; injunctive relief |
| Unfair Competition | Actual damages; disgorgement of profits |

---

## 10. Templates and Forms

### 10.1 Internal Incident Report Template

```
----------------------------------------------------------------------
IP INFRINGEMENT INCIDENT REPORT
----------------------------------------------------------------------

Report Number:       [INFR-YYYY-MM-NNN]
Date of Discovery:   [Date]
Reported By:         [Name]
Severity:            [CRITICAL / HIGH / MEDIUM / LOW]

INFRINGER INFORMATION
---------------------
Name:                [Name or "Unknown"]
Website/Platform:    [URL]
Contact Info:        [If available]
Location:            [If known]

INFRINGEMENT DETAILS
--------------------
Type:                [Course / Fork / Redistribution / Derivative / Other]
Description:         [Detailed description]
URL(s):              [Full URLs]
Date First Noticed:  [Date]

ORIGINAL WORK INFRINGED
-----------------------
Element:             [Architecture / Code / Prompts / Documentation / Design]
File/Path:           [Original file location]
License:             Proprietary

EVIDENCE COLLECTED
-----------------
[ ] Screenshots
[ ] Page archives
[ ] Source downloads
[ ] Correspondence
[ ] Side-by-side comparison

ACTION TAKEN
-----------
[ ] Cease and desist sent: [Date]
[ ] DMCA notice filed: [Date] at [Platform]
[ ] GitHub report filed: [Date]
[ ] Course platform report: [Date] at [Platform]
[ ] Legal counsel engaged: [Date]
[ ] Other: [Description]

STATUS:              [Open / In Progress / Resolved / Escalated]
RESOLVED DATE:       [Date]
NOTES:               [Any additional information]

----------------------------------------------------------------------
```

### 10.2 Infringement Evidence Log

```
----------------------------------------------------------------------
EVIDENCE LOG
----------------------------------------------------------------------

Item #:     [001]
Date:       [DD/MMM/YYYY]
Time:       [HH:MM Timezone]
Collected By: [Name]

Description: [Description of evidence item]

Source URL: [Full URL]

Storage Location: [File path or archive URL]

Hash:       [SHA-256 or MD5 hash for integrity verification]

Witness:    [Name of witness if applicable]

----------------------------------------------------------------------
```

### 10.3 Compliance Confirmation Request Template

After a cease and desist letter, send this confirmation request:

```
----------------------------------------------------------------------
COMPLIANCE CONFIRMATION REQUEST
----------------------------------------------------------------------

Date: [Date]

To: [Infringer Name]

Re: Confirmation of Compliance with Cease and Desist Demand

Dear [Name],

We acknowledge receipt of your response to our cease and desist letter
dated [Original Letter Date].

To confirm compliance, please provide:

1. Written confirmation that all infringing materials have been removed
   and will not be republished.

2. A list of all platforms and URLs from which materials were removed.

3. Confirmation that you have not retained any copies of the infringing
   materials in any form.

4. An accounting of all revenue received from the infringing activity.

5. Your undertaking not to engage in any further infringement.

Please provide this confirmation within seven (7) days.

Sincerely,

SoloCorp Organization Legal Department
----------------------------------------------------------------------
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | July 2026 | Legal (Tulya) | Initial enforcement guide |

**Classification:** Internal -- SoloCorp Organization Use
**Distribution:** Department Heads, Pipeline Auditor, Executive Team
**Review Cycle:** Quarterly or upon material change in IP posture
