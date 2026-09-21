/** The numbers, in plain text and nothing else: the fallback shown when a screen or the whole app has
 * failed must still be worth having in front of somebody. No icons, no links, no data from the box. */
export function EmergencyNumbers() {
  return (
    <section className="emergency-numbers" aria-label="If someone needs help now">
      <ul className="list" aria-label="Emergency numbers">
        <li><strong>999</strong> Emergency: ambulance, fire, police, coastguard</li>
        <li><strong>111</strong> NHS: urgent medical advice when it is not life-threatening</li>
        <li><strong>105</strong> Power cut: report it and get help from your network operator</li>
      </ul>
    </section>
  );
}
