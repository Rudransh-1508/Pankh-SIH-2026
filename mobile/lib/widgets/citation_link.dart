import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../theme.dart';

/// Where a Rule or benefit comes from. Tapping opens the official PDF at the cited page.
class CitationLink extends StatelessWidget {
  const CitationLink({super.key, required this.citation});

  final Citation citation;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: () => launchUrl(Uri.parse(citation.url), mode: LaunchMode.externalApplication),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.only(top: 2),
              child: Icon(Icons.description_outlined, size: 16, color: PankhColors.peacockDeep),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: l10n.sourcePage(citation.clause, citation.page),
                      style: text.labelMedium?.copyWith(
                        color: PankhColors.peacockDeep,
                        decoration: TextDecoration.underline,
                        decorationColor: PankhColors.peacockDeep.withValues(alpha: 0.4),
                      ),
                    ),
                    TextSpan(text: '  ·  ${citation.sourceTitle}', style: text.bodySmall),
                  ],
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
