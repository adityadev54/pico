class ComputerCommand {
  const ComputerCommand(this.kind, this.input, {this.deviceHint});
  final String kind;
  final Map<String, dynamic> input;
  final String? deviceHint;
}
