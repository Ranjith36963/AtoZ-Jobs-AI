interface Skill {
  name: string;
  esco_uri: string | null;
  skill_type: string | null;
  confidence: number | null;
  is_required: boolean;
}

interface SkillsPillsProps {
  skills: Skill[];
  maxVisible?: number;
}

export function SkillsPills({ skills, maxVisible = 5 }: SkillsPillsProps) {
  if (skills.length === 0) return null;

  const visible = skills.slice(0, maxVisible);
  const remaining = skills.length - maxVisible;

  return (
    <div className="flex flex-wrap gap-1.5" role="list" aria-label="Skills">
      {visible.map((skill) => {
        const baseClasses =
          "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium";
        const colorClasses = skill.is_required
          ? "bg-blue-100 text-blue-800 ring-1 ring-blue-300"
          : "bg-gray-100 text-gray-700";

        const pill = (
          <span className={`${baseClasses} ${colorClasses}`}>
            {skill.name}
          </span>
        );

        if (skill.esco_uri) {
          return (
            <a
              key={skill.name}
              href={skill.esco_uri}
              target="_blank"
              rel="noopener noreferrer"
              role="listitem"
              className="hover:opacity-80"
            >
              {pill}
            </a>
          );
        }

        return (
          <span key={skill.name} role="listitem">
            {pill}
          </span>
        );
      })}
      {remaining > 0 && (
        <span
          role="listitem"
          className="inline-flex items-center rounded-md bg-gray-50 px-2 py-0.5 text-xs font-medium text-gray-500"
        >
          +{remaining} more
        </span>
      )}
    </div>
  );
}
