interface CompanyInfoProps {
  company: {
    name: string;
    sic_codes: string[] | null;
    company_status: string | null;
    date_of_creation: string | null;
    website: string | null;
  } | null;
}

const SIC_SECTIONS: Record<string, string> = {
  "01": "Agriculture", "02": "Forestry", "03": "Fishing",
  "05": "Mining", "10": "Food", "13": "Textiles",
  "20": "Chemicals", "22": "Rubber", "24": "Metals",
  "25": "Metal products", "26": "Electronics", "27": "Electrical",
  "28": "Machinery", "29": "Motor vehicles", "30": "Transport equipment",
  "31": "Furniture", "32": "Other manufacturing",
  "35": "Energy", "36": "Water", "38": "Waste",
  "41": "Construction", "42": "Civil engineering",
  "45": "Motor trade", "46": "Wholesale", "47": "Retail",
  "49": "Transport", "50": "Water transport", "51": "Air transport",
  "52": "Warehousing", "53": "Postal",
  "55": "Accommodation", "56": "Food & beverage",
  "58": "Publishing", "59": "Media", "60": "Broadcasting",
  "61": "Telecoms", "62": "IT & Computing", "63": "Information services",
  "64": "Financial services", "65": "Insurance", "66": "Financial support",
  "68": "Real estate",
  "69": "Legal & accounting", "70": "Management consultancy",
  "71": "Architecture & engineering", "72": "R&D", "73": "Advertising",
  "74": "Professional services", "75": "Veterinary",
  "77": "Rental", "78": "Recruitment", "79": "Travel",
  "80": "Security", "81": "Facilities", "82": "Office admin",
  "84": "Public admin", "85": "Education",
  "86": "Healthcare", "87": "Residential care", "88": "Social work",
  "90": "Arts", "91": "Libraries & museums", "92": "Gambling",
  "93": "Sports", "94": "Membership orgs", "95": "Repair",
  "96": "Personal services", "97": "Households", "99": "International orgs",
};

function getSicLabel(code: string): string {
  const prefix = code.substring(0, 2);
  return SIC_SECTIONS[prefix] ?? `SIC ${code}`;
}

export function CompanyInfo({ company }: CompanyInfoProps) {
  if (!company) return null;

  return (
    <div className="rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900">Company Details</h3>
      <dl className="mt-3 space-y-2 text-sm">
        {company.sic_codes && company.sic_codes.length > 0 && (
          <div>
            <dt className="text-gray-500">Industry</dt>
            <dd className="text-gray-900">
              {company.sic_codes.map((c) => getSicLabel(c)).join(", ")}
            </dd>
          </div>
        )}
        {company.company_status && (
          <div>
            <dt className="text-gray-500">Status</dt>
            <dd className="capitalize text-gray-900">
              {company.company_status}
            </dd>
          </div>
        )}
        {company.date_of_creation && (
          <div>
            <dt className="text-gray-500">Established</dt>
            <dd className="text-gray-900">{company.date_of_creation}</dd>
          </div>
        )}
        {company.website && (
          <div>
            <dt className="text-gray-500">Website</dt>
            <dd>
              <a
                href={company.website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                {new URL(company.website).hostname}
              </a>
            </dd>
          </div>
        )}
      </dl>
    </div>
  );
}
