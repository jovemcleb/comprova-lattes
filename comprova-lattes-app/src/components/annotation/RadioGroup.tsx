interface Option<T extends string> {
  value: T
  label: string
}

interface RadioGroupProps<T extends string> {
  legend: string
  name: string
  options: readonly Option<T>[]
  value: T | null
  onChange: (value: T) => void
  disabled?: boolean
  disabledValues?: readonly T[]
  hint?: string
}

export function RadioGroup<T extends string>({ legend, name, options, value, onChange, disabled, disabledValues = [], hint }: RadioGroupProps<T>) {
  return (
    <fieldset disabled={disabled}>
      <legend>{legend}</legend>
      {hint && <p className="annot-note">{hint}</p>}
      <div className="annot-inline">
        {options.map(option => (
          <label className="checkbox" key={option.value}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              disabled={Boolean(disabled) || disabledValues.includes(option.value)}
              onChange={() => onChange(option.value)}
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  )
}
