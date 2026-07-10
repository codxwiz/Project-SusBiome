export const LEGAL_EFFECTIVE_DATE = "July 10, 2026";
export const LEGAL_YEAR = "2026";
export const LEGAL_EMAIL = "susbiome098@gmail.com";
export const LEGAL_WEBSITE = "https://susbiome.com";

export const legalPages = [
  {
    slug: "terms-conditions",
    title: "Terms & Conditions",
    shortTitle: "Terms",
    kicker: "Legal",
    description: "SusBiome Terms & Conditions for website, dashboard, API, and related service use.",
    updated: LEGAL_EFFECTIVE_DATE,
    lead:
      'Welcome to SusBiome. By accessing or using the SusBiome website, dashboard, APIs, or related services (collectively, the "Service"), you agree to be bound by these Terms & Conditions ("Terms"). If you do not agree to these Terms, you must not use the Service.',
    sections: [
      {
        heading: "1. About SusBiome",
        body: [
          "SusBiome is an environmental intelligence platform that integrates satellite observations, climate data, terrain information, and machine learning models to provide environmental risk assessments and decision-support information.",
          "The Service is intended to support research, planning, monitoring, and awareness. It is not intended to replace official government warnings, emergency management systems, or professional advice.",
        ],
      },
      {
        heading: "2. Eligibility",
        body: [
          "You must be at least 18 years old or have legal authority to enter into these Terms on behalf of an organization.",
        ],
      },
      {
        heading: "3. Acceptable Use",
        body: ["You agree not to:"],
        bullets: [
          "Use the Service for unlawful purposes.",
          "Attempt to gain unauthorized access to the Service or its infrastructure.",
          "Reverse engineer, copy, or redistribute proprietary components of the Service except where expressly permitted.",
          "Introduce malware, malicious code, or harmful automated requests.",
          "Interfere with the operation or security of the Service.",
        ],
      },
      {
        heading: "4. Accounts",
        body: [
          "If user accounts are available, you are responsible for maintaining the confidentiality of your credentials and for all activity under your account.",
        ],
      },
      {
        heading: "5. Data Sources",
        body: [
          "SusBiome integrates data from multiple third-party sources, including but not limited to satellite imagery, weather reanalysis products, environmental datasets, and publicly available geographic information.",
          "Each external dataset remains subject to its own license and terms of use.",
        ],
      },
      {
        heading: "6. Intellectual Property",
        body: [
          "Unless otherwise stated, all software, models, algorithms, visualizations, branding, documentation, and original content provided through SusBiome are the intellectual property of SusBiome or its licensors.",
          "You may not reproduce, modify, distribute, or commercially exploit any part of the Service without prior written permission.",
        ],
      },
      {
        heading: "7. Machine Learning Predictions",
        body: ["Risk scores, predictions, forecasts, and analytical outputs are generated using statistical and machine learning models. These outputs:"],
        bullets: [
          "are estimates only;",
          "may contain inaccuracies;",
          "should not be interpreted as guarantees;",
          "should always be considered alongside official guidance and local expertise.",
        ],
      },
      {
        heading: "8. No Emergency Service",
        body: [
          "SusBiome is not an emergency warning system.",
          "Users must rely on official government agencies for emergency alerts, evacuation orders, weather warnings, and disaster response information.",
        ],
      },
      {
        heading: "9. Availability",
        body: [
          "We aim to provide reliable access but do not guarantee uninterrupted or error-free availability.",
          "We may modify, suspend, or discontinue features at any time without notice.",
        ],
      },
      {
        heading: "10. Third-Party Services",
        body: [
          "The Service may link to or integrate with third-party platforms and datasets.",
          "SusBiome is not responsible for the availability, accuracy, or practices of third-party services.",
        ],
      },
      {
        heading: "11. Disclaimer",
        body: [
          'The Service is provided "as is" and "as available" without warranties of any kind, whether express or implied.',
          "To the fullest extent permitted by law, SusBiome disclaims all warranties, including merchantability, fitness for a particular purpose, and non-infringement.",
        ],
      },
      {
        heading: "12. Limitation of Liability",
        body: [
          "To the maximum extent permitted by law, SusBiome and its contributors shall not be liable for any direct, indirect, incidental, consequential, special, or exemplary damages arising from the use of the Service.",
        ],
      },
      {
        heading: "13. Indemnification",
        body: [
          "You agree to indemnify and hold harmless SusBiome, its operators, contributors, and affiliates from claims arising out of your misuse of the Service or violation of these Terms.",
        ],
      },
      {
        heading: "14. Changes",
        body: [
          "We may update these Terms periodically.",
          "Continued use of the Service after changes become effective constitutes acceptance of the revised Terms.",
        ],
      },
      {
        heading: "15. Governing Law",
        body: [
          "These Terms shall be governed by the laws applicable in the jurisdiction where SusBiome operates, unless otherwise required by applicable law.",
        ],
      },
      {
        heading: "16. Contact",
        body: [`Questions regarding these Terms may be directed to: Email: ${LEGAL_EMAIL}. Website: ${LEGAL_WEBSITE}.`],
      },
    ],
  },
  {
    slug: "privacy-policy",
    title: "Privacy Policy",
    shortTitle: "Privacy",
    kicker: "Privacy",
    description: "How SusBiome handles personal information, environmental data, cookies, and requests.",
    updated: LEGAL_EFFECTIVE_DATE,
    lead: "SusBiome respects your privacy and is committed to protecting your personal information.",
    sections: [
      {
        heading: "1. Information We Collect",
        body: [
          "Depending on how you use the Service, we may collect:",
        ],
        bullets: [
          "Name",
          "Email address",
          "Organization",
          "Account information",
          "Usage analytics",
          "Device and browser information",
          "IP address",
          "Log files",
          "Feedback and support communications",
        ],
      },
      {
        body: ["We do not intentionally collect sensitive personal information unless required for a specific feature."],
      },
      {
        heading: "2. Environmental Data",
        body: [
          "Most environmental, climate, satellite, and geographic datasets processed by SusBiome do not identify individuals.",
          "These datasets are used solely for environmental analysis and risk assessment.",
        ],
      },
      {
        heading: "3. How We Use Information",
        body: ["We use collected information to:"],
        bullets: [
          "provide the Service;",
          "improve platform performance;",
          "maintain security;",
          "respond to support requests;",
          "develop new features;",
          "generate aggregated analytics.",
        ],
      },
      {
        body: ["We do not sell personal information."],
      },
      {
        heading: "4. Cookies",
        body: [
          "The Service may use cookies and similar technologies for authentication, preferences, analytics, and security.",
          "You may configure your browser to refuse cookies, although some features may not function correctly.",
        ],
      },
      {
        heading: "5. Third-Party Services",
        body: [
          "We may use trusted third-party providers for hosting, analytics, authentication, storage, mapping, or communications.",
          "Those providers process data according to their own privacy policies.",
        ],
      },
      {
        heading: "6. Data Security",
        body: [
          "We implement reasonable administrative, technical, and organizational safeguards designed to protect personal information.",
          "However, no method of transmission or storage is completely secure.",
        ],
      },
      {
        heading: "7. Data Retention",
        body: ["We retain personal information only as long as necessary to:"],
        bullets: [
          "provide the Service;",
          "comply with legal obligations;",
          "resolve disputes;",
          "enforce agreements.",
        ],
      },
      {
        heading: "8. Your Rights",
        body: ["Where applicable, you may have the right to:"],
        bullets: [
          "access your personal information;",
          "correct inaccurate information;",
          "request deletion;",
          "object to certain processing;",
          "request data portability;",
          "withdraw consent where applicable.",
        ],
      },
      {
        body: ["Requests may be submitted using the contact details below."],
      },
      {
        heading: "9. Children's Privacy",
        body: [
          "The Service is not directed to children under 13 years of age, and we do not knowingly collect personal information from children.",
        ],
      },
      {
        heading: "10. International Users",
        body: [
          "Information may be processed in countries other than your own, subject to appropriate safeguards where required.",
        ],
      },
      {
        heading: "11. Changes",
        body: [
          "We may update this Privacy Policy periodically.",
          "The updated version will be posted on this page with a revised Effective Date.",
        ],
      },
      {
        heading: "12. Contact",
        body: [`For privacy-related questions or requests: Email: ${LEGAL_EMAIL}. Website: ${LEGAL_WEBSITE}.`],
      },
      {
        heading: "13. Open Data Attribution",
        body: [
          "SusBiome incorporates publicly available environmental and geospatial datasets from various organizations. Original ownership, licensing, and attribution remain with the respective data providers.",
          "Users should consult the applicable source licenses when reusing underlying datasets.",
        ],
      },
    ],
  },
  {
    slug: "copyright-intellectual-property",
    title: "Copyright & Intellectual Property",
    shortTitle: "Copyright",
    kicker: "Ownership",
    description: "Copyright and intellectual property notice for SusBiome content, software, models, and branding.",
    updated: LEGAL_EFFECTIVE_DATE,
    lead: `Copyright ${LEGAL_YEAR} SusBiome. All rights reserved.`,
    sections: [
      {
        body: [
          "The SusBiome name, logo, software, machine learning models, algorithms, dashboards, visualizations, documentation, and original content are protected by applicable intellectual property laws.",
          "Unless expressly permitted in writing, users may not:",
        ],
        bullets: [
          "reproduce or redistribute proprietary software;",
          "reverse engineer platform functionality;",
          "remove copyright notices;",
          "commercialize SusBiome content or software;",
          "use SusBiome branding without authorization.",
        ],
      },
      {
        body: [
          "Third-party datasets, trademarks, and logos remain the property of their respective owners.",
          "Nothing contained within the Service grants users ownership of SusBiome intellectual property beyond the limited license necessary to use the platform in accordance with the Terms & Conditions.",
        ],
      },
    ],
  },
  {
    slug: "ai-prediction-disclaimer",
    title: "AI & Prediction Disclaimer",
    shortTitle: "AI disclaimer",
    kicker: "Disclaimer",
    description: "Important limitations for SusBiome AI outputs, predictions, forecasts, and risk scores.",
    updated: LEGAL_EFFECTIVE_DATE,
    lead:
      "SusBiome provides environmental intelligence generated through statistical analysis, satellite observations, climate datasets, geographic information systems, and machine learning models.",
    sections: [
      {
        body: [
          "The information presented by SusBiome is intended solely for research, planning, education, environmental monitoring, and decision support.",
        ],
      },
      {
        heading: "No Guarantee",
        body: [
          "All predictions, forecasts, susceptibility maps, risk scores, and analytical outputs are probabilistic estimates.",
          "They should not be interpreted as guarantees that an event will or will not occur.",
        ],
      },
      {
        heading: "Not Emergency Advice",
        body: [
          "SusBiome is not an emergency warning system and should never replace official alerts issued by government agencies or emergency management authorities.",
          "Users should always follow official weather warnings, evacuation notices, and disaster response instructions.",
        ],
      },
      {
        heading: "Model Limitations",
        body: ["Predictions may be affected by:"],
        bullets: [
          "incomplete or delayed data;",
          "satellite coverage limitations;",
          "weather uncertainty;",
          "modelling assumptions;",
          "machine learning uncertainty;",
          "changing environmental conditions.",
        ],
      },
      {
        heading: "User Responsibility",
        body: [
          "Users remain solely responsible for decisions made using SusBiome.",
          "SusBiome shall not be liable for losses, damages, or consequences arising from reliance on predictions or analyses generated by the platform.",
        ],
      },
      {
        heading: "Continuous Improvement",
        body: [
          "Models are periodically updated as new data, methodologies, and scientific knowledge become available.",
          "Predictions may therefore change over time.",
          "Continued use of the platform constitutes acceptance of these limitations.",
        ],
      },
    ],
  },
  {
    slug: "cookie-policy",
    title: "Cookie Policy",
    shortTitle: "Cookies",
    kicker: "Cookies",
    description: "How SusBiome may use cookies and similar technologies.",
    updated: LEGAL_EFFECTIVE_DATE,
    lead:
      "SusBiome uses cookies and similar technologies to improve user experience, maintain security, and enhance platform performance.",
    sections: [
      {
        heading: "Types of Cookies",
        body: ["We may use:"],
        bullets: [
          "Essential cookies required for platform functionality.",
          "Authentication cookies to maintain user sessions.",
          "Preference cookies to remember user settings.",
          "Analytics cookies to understand how the platform is used.",
          "Performance cookies to improve reliability and speed.",
        ],
      },
      {
        heading: "Managing Cookies",
        body: [
          "Most browsers allow users to manage or disable cookies through browser settings.",
          "Disabling cookies may affect certain features of the Service.",
        ],
      },
      {
        heading: "Third-Party Cookies",
        body: [
          "Where third-party services are integrated, those providers may place cookies in accordance with their own privacy policies.",
        ],
      },
      {
        heading: "Changes",
        body: [
          "This Cookie Policy may be updated periodically. Continued use of the Service indicates acceptance of any revised version.",
        ],
      },
    ],
  },
  {
    slug: "open-data-attribution",
    title: "Open Data Attribution",
    shortTitle: "Data attribution",
    kicker: "Attribution",
    description: "Open data attribution notice for public environmental, climate, satellite, and geographic datasets.",
    updated: LEGAL_EFFECTIVE_DATE,
    lead:
      "SusBiome integrates numerous publicly available environmental, climate, satellite, and geographic datasets.",
    sections: [
      {
        body: [
          "Ownership of these datasets remains with their respective organizations.",
          "Examples of data providers include, but are not limited to:",
        ],
        bullets: [
          "NASA",
          "Copernicus Climate Change Service (ERA5)",
          "ECMWF",
          "ESA",
          "USGS",
          "NOAA",
          "OpenStreetMap contributors",
          "CHIRPS",
          "SMAP",
          "MODIS",
          "GPM IMERG",
        ],
      },
      {
        body: [
          "Each dataset remains subject to its original license, attribution requirements, and usage conditions.",
          "SusBiome adds value through data integration, quality assurance, feature engineering, machine learning, environmental modelling, and visualization.",
          "Users wishing to reuse underlying datasets should consult the original providers for applicable licensing requirements.",
        ],
      },
    ],
  },
];

export function getLegalPage(slug) {
  return legalPages.find((page) => page.slug === slug);
}
